"""Background loop: sample CPU and publish rolling window averages."""
from __future__ import annotations

import asyncio
import logging

from app.constants.system_metrics import (
    SYSTEM_METRICS_SAMPLE_INTERVAL_SEC,
    SYSTEM_METRICS_STARTUP_DELAY_SEC,
)
from app.services.system_metrics.collector import get_collector

log = logging.getLogger("waf.system_metrics.worker")


async def _wait_or_stop(stop: asyncio.Event | None, timeout: float) -> bool:
    """Sleep `timeout` seconds, or until stop is set. Returns True if stopped."""
    if timeout <= 0:
        return bool(stop and stop.is_set())
    if stop is None:
        await asyncio.sleep(timeout)
        return False
    try:
        await asyncio.wait_for(stop.wait(), timeout=timeout)
        return True
    except TimeoutError:
        return False


async def run_system_metrics_loop(stop: asyncio.Event | None = None) -> None:
    collector = get_collector()
    log.info(
        "system metrics collector waiting %ss after startup before sampling (interval=%ss)",
        SYSTEM_METRICS_STARTUP_DELAY_SEC,
        SYSTEM_METRICS_SAMPLE_INTERVAL_SEC,
    )
    if await _wait_or_stop(stop, SYSTEM_METRICS_STARTUP_DELAY_SEC):
        return

    log.info("system metrics collector started")
    # Prime one sample so the first delta-based CPU% can appear on the next tick.
    collector.tick()
    while stop is None or not stop.is_set():
        try:
            snapshot = collector.tick()
            await collector.publish(snapshot)
        except Exception:  # noqa: BLE001
            log.exception("system metrics tick failed")

        if await _wait_or_stop(stop, SYSTEM_METRICS_SAMPLE_INTERVAL_SEC):
            break
