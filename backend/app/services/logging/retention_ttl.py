"""Apply ClickHouse log retention TTL from admin settings."""
from __future__ import annotations

import asyncio
import logging

from app.constants.logging_settings import DEFAULT_LOG_RETENTION_DAYS
from app.core.clickhouse import get_clickhouse
from app.core.db import SessionLocal
from app.services import waf_settings

log = logging.getLogger("waf.retention_ttl")

_last_applied_days: int | None = None

_LOG_TABLES: tuple[tuple[str, str], ...] = (
    ("waf_logs", "toDateTime(ts) + INTERVAL {days} DAY"),
    ("mv_stats_core_hourly", "hour + INTERVAL {days} DAY"),
)


def clamp_retention_days(days: int) -> int:
    return max(1, min(int(days), 365))


async def fetch_retention_days() -> int:
    async with SessionLocal() as db:
        row = await waf_settings.get_or_create(db)
        return clamp_retention_days(
            getattr(row, "log_retention_days", None) or DEFAULT_LOG_RETENTION_DAYS
        )


def _apply_ttl_sync(days: int) -> None:
    client = get_clickhouse()
    for table, expr_tpl in _LOG_TABLES:
        try:
            client.command(f"ALTER TABLE {table} MODIFY TTL {expr_tpl.format(days=days)}")
        except Exception:  # noqa: BLE001
            log.exception("failed to apply TTL on %s", table)


async def apply_log_retention_ttl(days: int | None = None) -> int:
    """Sync ClickHouse TTL with configured retention; skip if unchanged in-process."""
    global _last_applied_days

    if days is None:
        days = await fetch_retention_days()
    else:
        days = clamp_retention_days(days)

    if _last_applied_days == days:
        return days

    await asyncio.to_thread(_apply_ttl_sync, days)
    _last_applied_days = days
    log.info("clickhouse log TTL set to %d days", days)
    return days
