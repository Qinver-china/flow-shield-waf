"""Daily certificate expiry notification loop."""
from __future__ import annotations

import asyncio
import logging

from app.core.db import SessionLocal
from app.services.notifications.certificate_expiry import run_certificate_expiry_checks

log = logging.getLogger("waf.worker.cert_expiry")


async def run_certificate_expiry_loop(stop: asyncio.Event, interval_sec: int = 60) -> None:
    while not stop.is_set():
        try:
            async with SessionLocal() as db:
                sent = await run_certificate_expiry_checks(db)
                if sent:
                    log.info("certificate expiry notices sent: %d", sent)
        except Exception:  # noqa: BLE001
            log.exception("certificate expiry loop failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_sec)
        except TimeoutError:
            continue
