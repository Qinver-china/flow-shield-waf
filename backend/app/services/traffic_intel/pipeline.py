"""Orchestrates ingest → baseline refresh → anomaly detection → actions."""
from __future__ import annotations

import asyncio
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.services.traffic_intel.actions import ActionDispatcher
from app.services.traffic_intel.baseline import BaselineCalculator
from app.services.traffic_intel.constants import (
    DEFAULT_ALERT_COOLDOWN_SEC,
    DEFAULT_BASELINE_LOOKBACK_DAYS,
    DEFAULT_BASELINE_RECALC_INTERVAL_SEC,
    DEFAULT_INGEST_INTERVAL_SEC,
    DEFAULT_MIN_BASELINE_SAMPLES,
    DEFAULT_SPIKE_RATIO,
)
from app.services.traffic_intel.detector import AnomalyDetector
from app.services.traffic_intel.ingest import SnapshotIngestor
from app.services.traffic_intel.store.alerts_mysql import AlertStore
from app.services.traffic_intel.redis_baselines import publish_baselines_to_redis
from app.services.traffic_intel.types import TrafficIntelConfig

log = logging.getLogger("waf.traffic_intel.pipeline")


class TrafficIntelPipeline:
    """Main entry for the traffic intelligence worker loop."""

    def __init__(
        self,
        config: TrafficIntelConfig | None = None,
        ingestor: SnapshotIngestor | None = None,
        baseline_calc: BaselineCalculator | None = None,
        detector: AnomalyDetector | None = None,
        dispatcher: ActionDispatcher | None = None,
        alert_store: AlertStore | None = None,
    ):
        self.config = config or TrafficIntelConfig(
            spike_ratio=DEFAULT_SPIKE_RATIO,
            baseline_lookback_days=DEFAULT_BASELINE_LOOKBACK_DAYS,
            min_baseline_samples=DEFAULT_MIN_BASELINE_SAMPLES,
            alert_cooldown_sec=DEFAULT_ALERT_COOLDOWN_SEC,
        )
        self._ingestor = ingestor or SnapshotIngestor()
        self._baseline = baseline_calc or BaselineCalculator()
        self._detector = detector or AnomalyDetector()
        self._dispatcher = dispatcher or ActionDispatcher()
        self._alerts = alert_store or AlertStore()
        self._last_baseline_at = 0.0

    async def run_once(self) -> None:
        if not self.config.enabled:
            return

        await self._ingestor.ingest_once()

        async with SessionLocal() as db:
            now = time.monotonic()
            if now - self._last_baseline_at >= DEFAULT_BASELINE_RECALC_INTERVAL_SEC:
                await self._baseline.recalculate(db, self.config, site_ids=[None])
                await publish_baselines_to_redis(db)
                self._last_baseline_at = now

            anomalies = await self._detector.evaluate_scope(
                db, self.config, site_id=None
            )
            filtered = await self._filter_cooldown(db, anomalies)
            if filtered:
                await self._dispatcher.dispatch(db, filtered, self.config)

    async def _filter_cooldown(
        self,
        db: AsyncSession,
        anomalies: list,
    ) -> list:
        kept = []
        for a in anomalies:
            recent = await self._alerts.recent_open_count(
                db,
                site_id=a.site_id,
                window_sec=a.window_sec,
                within_sec=self.config.alert_cooldown_sec,
            )
            if recent == 0:
                kept.append(a)
        return kept


async def run_pipeline_loop(
    stop_event=None,
    interval_sec: int = DEFAULT_INGEST_INTERVAL_SEC,
) -> None:
    pipeline = TrafficIntelPipeline()
    await asyncio.to_thread(pipeline._ingestor._store.ensure_schema)
    log.info("traffic intel pipeline started (interval=%ss)", interval_sec)
    while stop_event is None or not stop_event.is_set():
        try:
            await pipeline.run_once()
        except Exception:  # noqa: BLE001
            log.exception("traffic intel pipeline tick failed")
        if stop_event is not None:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_sec)
                break
            except TimeoutError:
                continue
        else:
            await asyncio.sleep(interval_sec)
