"""Worker entrypoint: log consumer + retention. Run with `python -m app.workers.runner`."""
import asyncio
import logging

from app.core.logging import setup_logging
from app.services.ai_guard.worker import run_ai_guard_loop
from app.services.logging.collector import run_consumer
from app.services.traffic_intel.pipeline import run_pipeline_loop
from app.workers.alerts import run_alert_loop
from app.workers.retention import run_retention

log = logging.getLogger("waf.worker")


async def main() -> None:
    setup_logging()
    log.info("worker starting")
    stop = asyncio.Event()
    await asyncio.gather(
        run_consumer(stop),
        run_retention(stop),
        run_pipeline_loop(stop),
        run_ai_guard_loop(stop),
        run_alert_loop(stop),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
