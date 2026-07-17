"""Periodic log retention / cleanup task."""
import asyncio
import logging

from app.services.logging.retention_ttl import apply_log_retention_ttl

log = logging.getLogger("waf.retention")

INTERVAL_SECONDS = 3600


async def run_retention(stop_event: asyncio.Event | None = None) -> None:
    days = await apply_log_retention_ttl()
    log.info("retention task started (keep %d days, clickhouse TTL)", days)
    while stop_event is None or not stop_event.is_set():
        try:
            await apply_log_retention_ttl()
        except Exception:  # noqa: BLE001
            log.exception("retention check failed")
        await asyncio.sleep(INTERVAL_SECONDS)
