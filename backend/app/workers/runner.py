"""Worker entrypoint: log consumer + retention. Run with `python -m app.workers.runner`."""
import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.core.logging import setup_logging
from app.services.ai_guard.worker import run_ai_guard_loop
from app.services.logging.collector import run_consumer
from app.services.system_metrics.worker import run_system_metrics_loop
from app.services.traffic_intel.live_backup import run_traffic_live_backup_loop
from app.services.traffic_intel.pipeline import run_pipeline_loop
from app.workers.alerts import run_alert_loop
from app.workers.certificate_expiry import run_certificate_expiry_loop
from app.workers.retention import run_retention

log = logging.getLogger("waf.worker")

RESTART_DELAY_SEC = 5.0

WorkerFn = Callable[[asyncio.Event], Awaitable[None]]


async def _run_supervised(name: str, fn: WorkerFn, stop: asyncio.Event) -> None:
    """Run a worker loop; restart on crash so one failure cannot stop siblings."""
    while not stop.is_set():
        try:
            await fn(stop)
            return
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("%s crashed; restarting in %.0fs", name, RESTART_DELAY_SEC)
            try:
                await asyncio.wait_for(stop.wait(), timeout=RESTART_DELAY_SEC)
                return
            except TimeoutError:
                continue


async def main() -> None:
    setup_logging()
    log.info("worker starting")
    stop = asyncio.Event()
    await asyncio.gather(
        _run_supervised("log_collector", run_consumer, stop),
        _run_supervised("retention", run_retention, stop),
        _run_supervised("traffic_pipeline", run_pipeline_loop, stop),
        _run_supervised("traffic_live_backup", run_traffic_live_backup_loop, stop),
        _run_supervised("ai_guard", run_ai_guard_loop, stop),
        _run_supervised("alerts", run_alert_loop, stop),
        _run_supervised("certificate_expiry", run_certificate_expiry_loop, stop),
        _run_supervised("system_metrics", run_system_metrics_loop, stop),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
