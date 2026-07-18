"""ClickHouse schema patches for log storage."""
from __future__ import annotations

import logging

from app.core.clickhouse import get_clickhouse

log = logging.getLogger("waf.clickhouse_patches")

_BOT_COLUMNS = (
    ("bot_name", "LowCardinality(Nullable(String))"),
    ("bot_category", "LowCardinality(Nullable(String))"),
)


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
