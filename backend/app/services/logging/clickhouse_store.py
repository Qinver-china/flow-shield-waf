"""ClickHouse log storage backend."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.core.clickhouse import get_clickhouse
from app.services.logging.enrich import enrich_entry

log = logging.getLogger("waf.clickhouse_store")

_COLUMNS = [
    "ts", "site_id", "domain", "client_ip", "ip_is_private", "xff_first",
    "geo_country", "geo_region", "geo_city", "geo_isp", "geo_ip_type", "geo_asn",
    "method", "scheme", "http_version", "uri", "uri_path", "uri_ext", "uri_depth",
    "uri_pattern", "query_count", "referer_host", "ua", "bot_name", "bot_category",
    "ua_family", "ua_os",
    "ua_browser", "tls_version", "tls_cipher", "tls_ja3", "rule_id", "rule_name",
    "source", "mode", "action", "blocked", "log_type", "request_id", "evaluated",
    "payload",
]


def _ts_value(entry: dict) -> datetime:
    ts = entry.get("ts")
    if isinstance(ts, datetime):
        return ts.replace(tzinfo=None)
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
    return datetime.utcnow()


def _json_str(value) -> str:
    if value is None:
        return "{}"
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"


def _row_from_entry(entry: dict) -> list:
    e = enrich_entry(entry)
    ts = _ts_value(e)
    blocked = bool(e.get("blocked"))
    ip_priv = e.get("ip_is_private")
    if isinstance(ip_priv, str):
        ip_priv = ip_priv == "true" or ip_priv == "1"
    return [
        ts,
        e.get("site_id"),
        e.get("domain") or "",
        e.get("client_ip") or "",
        1 if ip_priv else 0,
        e.get("xff_first"),
        e.get("geo_country"),
        e.get("geo_region"),
        e.get("geo_city"),
        e.get("geo_isp"),
        e.get("geo_ip_type"),
        e.get("geo_asn"),
        e.get("method") or "",
        e.get("scheme") or "",
        e.get("http_version") or "",
        e.get("uri") or "",
        e.get("uri_path") or "",
        e.get("uri_ext") or "",
        int(e.get("uri_depth") or 0),
        e.get("uri_pattern") or "",
        int(e.get("query_count") or 0),
        e.get("referer_host"),
        e.get("ua") or "",
        e.get("bot_name"),
        e.get("bot_category"),
        e.get("ua_family"),
        e.get("ua_os"),
        e.get("ua_browser"),
        e.get("tls_version"),
        e.get("tls_cipher"),
        e.get("tls_ja3"),
        e.get("rule_id"),
        e.get("rule_name"),
        e.get("source") or "",
        e.get("mode") or "",
        e.get("action") or e.get("mode") or "",
        1 if blocked else 0,
        e.get("log_type") or "protection",
        e.get("request_id") or "",
        _json_str(e.get("evaluated")),
        _json_str(e.get("payload") if e.get("payload") is not None else {
            k: e[k] for k in ("client", "request", "headers", "cookies", "query")
            if k in e
        }),
    ]


class ClickHouseLogStore:
    async def add_many(self, entries: list[dict]) -> int:
        if not entries:
            return 0
        rows = [_row_from_entry(e) for e in entries]
        client = get_clickhouse()

        def _insert():
            client.insert("waf_logs", rows, column_names=_COLUMNS)

        await asyncio.to_thread(_insert)
        return len(rows)

    async def ensure_schema(self) -> None:
        try:
            client = get_clickhouse()
            ddl_path = "/app/deploy/clickhouse/init.sql"
            try:
                with open(ddl_path, encoding="utf-8") as f:
                    sql = f.read()
                for stmt in sql.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        client.command(stmt)
            except OSError:
                client.command(
                    "CREATE TABLE IF NOT EXISTS waf_logs ("
                    "ts DateTime64(3), site_id Nullable(UInt32), domain String, "
                    "client_ip String, blocked UInt8, log_type String, request_id String"
                    ") ENGINE = MergeTree ORDER BY (ts)"
                )
        except Exception:  # noqa: BLE001
            log.exception("clickhouse ensure_schema failed")
