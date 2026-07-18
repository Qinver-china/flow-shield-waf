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

_HOURLY_MV = "mv_stats_core_hourly_mv"


def ensure_clickhouse_columns() -> None:
    try:
        client = get_clickhouse()
        for col, col_type in _BOT_COLUMNS:
            client.command(
                f"ALTER TABLE waf_logs ADD COLUMN IF NOT EXISTS {col} {col_type}"
            )
            log.info("clickhouse column ensured: waf_logs.%s", col)
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
