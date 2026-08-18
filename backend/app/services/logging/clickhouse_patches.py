"""ClickHouse schema patches for log storage."""
from __future__ import annotations

import logging

from app.core.clickhouse import get_clickhouse
from app.core.config import settings

log = logging.getLogger("waf.clickhouse_patches")

_BOT_COLUMNS = (
    ("bot_name", "LowCardinality(Nullable(String))"),
    ("bot_category", "LowCardinality(Nullable(String))"),
)

_URI_COLUMNS = (
    ("uri_query", "String DEFAULT ''"),
    ("referer", "String DEFAULT ''"),
)

_TCP_IP_COLUMNS = (
    ("tcp_ip", "String DEFAULT ''"),
)

_HOURLY_MV = "mv_stats_core_hourly_mv"


def ensure_clickhouse_columns() -> None:
    try:
        client = get_clickhouse()
        rows = client.query(
            "SELECT name FROM system.columns "
            "WHERE database = {db:String} AND table = 'waf_logs'",
            parameters={"db": settings.clickhouse_database},
        ).result_rows
        col_names = {str(row[0]) for row in rows}
        if "uri" in col_names and "request_uri" not in col_names:
            client.command("ALTER TABLE waf_logs RENAME COLUMN uri TO request_uri")
            log.info("clickhouse column renamed: waf_logs.uri -> request_uri")
        elif "request_uri" not in col_names:
            client.command(
                "ALTER TABLE waf_logs ADD COLUMN IF NOT EXISTS request_uri String DEFAULT ''"
            )
            log.info("clickhouse column ensured: waf_logs.request_uri")
        for col, col_type in _BOT_COLUMNS:
            client.command(
                f"ALTER TABLE waf_logs ADD COLUMN IF NOT EXISTS {col} {col_type}"
            )
            log.info("clickhouse column ensured: waf_logs.%s", col)
        for col, col_type in _URI_COLUMNS:
            client.command(
                f"ALTER TABLE waf_logs ADD COLUMN IF NOT EXISTS {col} {col_type}"
            )
            log.info("clickhouse column ensured: waf_logs.%s", col)
        for col, col_type in _TCP_IP_COLUMNS:
            client.command(
                f"ALTER TABLE waf_logs ADD COLUMN IF NOT EXISTS {col} {col_type}"
            )
            log.info("clickhouse column ensured: waf_logs.%s", col)
        if "geo_ip_type" in col_names:
            client.command("ALTER TABLE waf_logs DROP COLUMN IF EXISTS geo_ip_type")
            log.info("clickhouse column dropped: waf_logs.geo_ip_type")
    except Exception:  # noqa: BLE001
        log.exception("clickhouse column patch failed")


def _mv_is_attached(client) -> bool:
    rows = client.query(
        "SELECT count() FROM system.tables "
        "WHERE database = {db:String} AND name = {name:String}",
        parameters={"db": settings.clickhouse_database, "name": _HOURLY_MV},
    ).result_rows
    return bool(rows and int(rows[0][0]) > 0)


def ensure_hourly_mv_state(enabled: bool | None = None) -> None:
    """Attach/detach hourly stats MV on the ingest hot path (storage unchanged)."""
    enabled = settings.clickhouse_hourly_mv_enabled if enabled is None else enabled
    try:
        client = get_clickhouse()
        attached = _mv_is_attached(client)
        if enabled and not attached:
            client.command(f"ATTACH TABLE IF NOT EXISTS {_HOURLY_MV}")
            log.info("clickhouse hourly MV attached: %s", _HOURLY_MV)
        elif not enabled and attached:
            client.command(f"DETACH TABLE IF EXISTS {_HOURLY_MV}")
            log.info(
                "clickhouse hourly MV detached for ingest performance: %s "
                "(set CLICKHOUSE_HOURLY_MV_ENABLED=true to re-enable)",
                _HOURLY_MV,
            )
    except Exception:  # noqa: BLE001
        log.exception("clickhouse hourly MV state patch failed")
