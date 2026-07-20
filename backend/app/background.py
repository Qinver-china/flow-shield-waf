"""Background tasks for the FastAPI process."""
from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.db import SessionLocal
from app.services import rule_sync
from app.services.crawler_vendored.sync import maybe_auto_sync

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


async def run_crawler_vendored_auto_sync(stop: asyncio.Event) -> None:
    interval = max(300, settings.crawler_vendored_check_interval_sec)
    while not stop.is_set():
        try:
            async with SessionLocal() as db:
                await maybe_auto_sync(db)
        except Exception:  # noqa: BLE001
            log.exception("crawler vendored auto-sync failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            continue
