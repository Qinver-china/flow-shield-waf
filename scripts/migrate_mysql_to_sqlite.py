#!/usr/bin/env python3
"""One-shot migration: MySQL config tables -> SQLite; optional flow tables -> ClickHouse.

Usage (from repo root, with MySQL still running):
  pip install aiosqlite aiomysql clickhouse-connect sqlalchemy
  python scripts/migrate_mysql_to_sqlite.py \\
    --sqlite-path ./waf.db \\
    --mysql-url 'mysql+aiomysql://waf:pass@127.0.0.1:3306/waf' \\
    --import-clickhouse-flow

Environment variables (alternative to flags):
  DB_PATH, MYSQL_* / DB_HOST / DB_PORT, CLICKHOUSE_*
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.ext.asyncio import create_async_engine

# Tables kept in SQLite (config + chat + baselines)
SQLITE_TABLES = (
    "admin_user",
    "site",
    "certificate",
    "rule",
    "bot_category",
    "bot_profile",
    "ip_group",
    "ip_list",
    "exception",
    "rate_limit",
    "waf_setting",
    "notification_channel",
    "alert_policy",
    "traffic_baseline",
    "ai_guard_setting",
    "ai_guard_policy",
    "ai_guard_chat_session",
    "ai_guard_chat_message",
)

FLOW_TABLES = (
    "ai_guard_incident",
    "alert_notification_log",
    "traffic_alert",
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Migrate MySQL data to SQLite (+ optional ClickHouse flow)")
    p.add_argument("--sqlite-path", default=os.getenv("DB_PATH", "/data/waf.db"))
    p.add_argument(
        "--mysql-url",
        default=os.getenv("MYSQL_DATABASE_URL") or _default_mysql_url(),
    )
    p.add_argument("--import-clickhouse-flow", action="store_true")
    p.add_argument(
        "--flow-only",
        action="store_true",
        help="仅导入 MySQL 流水表到 ClickHouse（跳过 SQLite 配置迁移，用于补跑）",
    )
    p.add_argument("--clickhouse-host", default=os.getenv("CLICKHOUSE_HOST", "clickhouse"))
    p.add_argument("--clickhouse-port", type=int, default=int(os.getenv("CLICKHOUSE_PORT", "8123")))
    p.add_argument("--clickhouse-user", default=os.getenv("CLICKHOUSE_USER", "default"))
    p.add_argument("--clickhouse-password", default=os.getenv("CLICKHOUSE_PASSWORD", ""))
    p.add_argument("--clickhouse-database", default=os.getenv("CLICKHOUSE_DATABASE", "waf"))
    return p.parse_args()


def _default_mysql_url() -> str:
    user = os.getenv("MYSQL_USER", os.getenv("DB_USER", "waf"))
    password = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD", "waf"))
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "waf"))
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


async def _copy_sqlite_tables(mysql_url: str, sqlite_path: str) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "backend"))

    from app.models import Base
    from app.services.schema_patches import apply_schema_patches

    sqlite_path = str(Path(sqlite_path).resolve())
    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    if Path(sqlite_path).exists():
        print(f"WARNING: {sqlite_path} exists; rows will be appended where PK conflicts may fail")

    mysql_engine = create_async_engine(mysql_url)
    sqlite_engine = create_async_engine(f"sqlite+aiosqlite:///{sqlite_path}")

    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await apply_schema_patches(conn)

    mysql_meta = MetaData()
    async with mysql_engine.connect() as mysql_conn:
        await mysql_conn.run_sync(mysql_meta.reflect)
        for table_name in SQLITE_TABLES:
            if table_name not in mysql_meta.tables:
                print(f"skip missing mysql table: {table_name}")
                continue
            src: Table = mysql_meta.tables[table_name]
            result = await mysql_conn.execute(select(src))
            rows = result.mappings().all()
            if not rows:
                print(f"{table_name}: 0 rows")
                continue
            async with sqlite_engine.begin() as sqlite_conn:
                dest_meta = MetaData()
                await sqlite_conn.run_sync(dest_meta.reflect)
                if table_name not in dest_meta.tables:
                    print(f"skip missing sqlite table: {table_name}")
                    continue
                dest = dest_meta.tables[table_name]
                payload = [dict(r) for r in rows]
                await sqlite_conn.execute(dest.insert(), payload)
            print(f"{table_name}: migrated {len(rows)} rows")

    await mysql_engine.dispose()
    await sqlite_engine.dispose()
    print(f"SQLite config DB ready at {sqlite_path}")


def _import_flow_to_clickhouse(mysql_url: str, args: argparse.Namespace) -> None:
    import clickhouse_connect

    sync_mysql = create_engine(mysql_url.replace("+aiomysql", "+pymysql"))
    client = clickhouse_connect.get_client(
        host=args.clickhouse_host,
        port=args.clickhouse_port,
        username=args.clickhouse_user,
        password=args.clickhouse_password,
        database=args.clickhouse_database,
    )

    from app.services.analytics.clickhouse_schema import ensure_analytics_schema

    ensure_analytics_schema()

    try:
        with sync_mysql.connect() as conn:
            insp = inspect(sync_mysql)
            if insp.has_table("ai_guard_incident"):
                rows = conn.execute(text("SELECT * FROM ai_guard_incident ORDER BY id")).mappings().all()
                if rows:
                    ch_rows = []
                    for r in rows:
                        created = r.get("created_at") or datetime.utcnow()
                        updated = r.get("updated_at") or created
                        ch_rows.append([
                            int(r["id"]),
                            1,
                            r.get("policy_id"),
                            r.get("site_id"),
                            r.get("status") or "pending",
                            json.dumps(r.get("trigger_snapshot") or {}, ensure_ascii=False, default=str),
                            json.dumps(r.get("log_sample_meta") or {}, ensure_ascii=False, default=str),
                            json.dumps(r.get("analysis_report") or {}, ensure_ascii=False, default=str),
                            json.dumps(r.get("suggested_rule") or {}, ensure_ascii=False, default=str),
                            r.get("applied_rule_id"),
                            r.get("apply_mode"),
                            r.get("error_detail"),
                            json.dumps(r.get("notification_log") or [], ensure_ascii=False, default=str),
                            created,
                            updated,
                        ])
                    client.insert(
                        "ai_guard_incidents",
                        ch_rows,
                        column_names=[
                            "incident_id", "version", "policy_id", "site_id", "status",
                            "trigger_snapshot", "log_sample_meta", "analysis_report", "suggested_rule",
                            "applied_rule_id", "apply_mode", "error_detail", "notification_log",
                            "created_at", "updated_at",
                        ],
                    )
                    print(f"ai_guard_incidents: imported {len(ch_rows)} rows")

            if insp.has_table("alert_notification_log"):
                rows = conn.execute(text("SELECT * FROM alert_notification_log ORDER BY id")).mappings().all()
                if rows:
                    ch_rows = [
                        [
                            int(r["id"]),
                            int(r["policy_id"]),
                            int(r["channel_id"]),
                            r["status"],
                            r["message"],
                            r.get("detail"),
                            r.get("created_at") or datetime.utcnow(),
                        ]
                        for r in rows
                    ]
                    client.insert(
                        "alert_notification_logs",
                        ch_rows,
                        column_names=["id", "policy_id", "channel_id", "status", "message", "detail", "created_at"],
                    )
                    print(f"alert_notification_logs: imported {len(ch_rows)} rows")

            if insp.has_table("traffic_alert"):
                rows = conn.execute(text("SELECT * FROM traffic_alert ORDER BY id")).mappings().all()
                if rows:
                    ch_rows = [
                        [
                            int(r["id"]),
                            r.get("site_id"),
                            int(r["window_sec"]),
                            int(r["current_requests"]),
                            float(r["baseline_avg"]),
                            float(r["deviation_ratio"]),
                            r["severity"],
                            r["status"],
                            r["message"],
                            r["detected_at"],
                            r.get("created_at") or r["detected_at"],
                        ]
                        for r in rows
                    ]
                    client.insert(
                        "traffic_alerts",
                        ch_rows,
                        column_names=[
                            "id", "site_id", "window_sec", "current_requests", "baseline_avg",
                            "deviation_ratio", "severity", "status", "message", "detected_at", "created_at",
                        ],
                    )
                    print(f"traffic_alerts: imported {len(ch_rows)} rows")
    finally:
        sync_mysql.dispose()


async def main() -> None:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "backend"))

    if args.flow_only:
        args.import_clickhouse_flow = True

    if not args.flow_only:
        await _copy_sqlite_tables(args.mysql_url, args.sqlite_path)
    if args.import_clickhouse_flow:
        try:
            _import_flow_to_clickhouse(args.mysql_url, args)
        except ImportError as exc:
            print(f"ClickHouse flow import skipped (missing dependency): {exc}")


if __name__ == "__main__":
    asyncio.run(main())
