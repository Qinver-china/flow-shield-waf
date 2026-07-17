"""Independent alert policy evaluation loop."""
from __future__ import annotations

import asyncio
import logging

from app.core.db import SessionLocal
from app.services.notifications.evaluator import run_alert_policies

log = logging.getLogger("waf.worker.alerts")


async def run_alert_loop(stop: asyncio.Event, interval_sec: int = 60) -> None:
    while not stop.is_set():
        try:
            async with SessionLocal() as db:
                fired = await run_alert_policies(db)
                if fired:
                    log.info("alert policies fired: %d", fired)
        except Exception:  # noqa: BLE001
            log.exception("alert policy loop failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_sec)
        except TimeoutError:
            continue
