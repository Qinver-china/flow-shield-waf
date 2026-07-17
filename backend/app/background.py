"""Background tasks for the FastAPI process."""
from __future__ import annotations

import asyncio
import logging

from app.core.db import SessionLocal
from app.services import rule_sync

log = logging.getLogger("waf.background")


async def run_config_sync_retry(stop: asyncio.Event, interval_sec: int = 30) -> None:
    while not stop.is_set():
        try:
            async with SessionLocal() as db:
                await rule_sync.retry_if_dirty(db)
        except Exception:  # noqa: BLE001
            log.exception("config sync retry failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_sec)
        except TimeoutError:
            continue
