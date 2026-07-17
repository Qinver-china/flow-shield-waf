"""Anomaly detection: compare current traffic against learned baseline."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.traffic_intel.store.baseline_mysql import BaselineStore
from app.services.traffic_intel.store.clickhouse import ClickHouseTrafficStore
from app.services.traffic_intel.types import (
    AlertSeverity,
    AnomalyResult,
    Baseline,
    TrafficIntelConfig,
)
from app.services.traffic_intel.windows import label

log = logging.getLogger("waf.traffic_intel.detector")


class AnomalyDetector:
    """Flag traffic spikes when current > baseline * (1 + spike_ratio)."""

    def __init__(
        self,
        ch_store: ClickHouseTrafficStore | None = None,
        baseline_store: BaselineStore | None = None,
    ):
        self._ch = ch_store or ClickHouseTrafficStore()
        self._baselines = baseline_store or BaselineStore()

    async def evaluate_scope(
        self,
        db: AsyncSession,
        config: TrafficIntelConfig,
        *,
        site_id: int | None = None,
        as_of: datetime | None = None,
    ) -> list[AnomalyResult]:
        if not config.enabled:
            return []

        as_of = as_of or datetime.utcnow()
        anomalies: list[AnomalyResult] = []
        for window_sec in config.analysis_windows_sec:
            baseline = await self._baselines.get(
                db, site_id=site_id, window_sec=window_sec, as_of=as_of
            )
            if baseline is None or baseline.avg_requests <= 0:
                continue
            if baseline.sample_count < config.min_baseline_samples:
                continue

            current = await asyncio.to_thread(
                self._ch.current_window_requests,
                window_sec,
                site_id=site_id,
                as_of=as_of,
            )
            result = self._compare(current, baseline, config, as_of)
            if result is not None:
                anomalies.append(result)
        return anomalies

    def _compare(
        self,
        current: int,
        baseline: Baseline,
        config: TrafficIntelConfig,
        as_of: datetime,
    ) -> AnomalyResult | None:
        threshold = baseline.avg_requests * (1 + config.spike_ratio)
        if current <= threshold:
            return None

        ratio = current / baseline.avg_requests
        severity = (
            AlertSeverity.CRITICAL
            if ratio >= 1 + config.spike_ratio * 2
            else AlertSeverity.WARNING
        )
        scope = "全站" if baseline.site_id is None else f"站点 #{baseline.site_id}"
        win = label(baseline.window_sec)
        pct = int((ratio - 1) * 100)
        message = (
            f"{scope} {win} 请求量 {current}，"
            f"高于基线 {baseline.avg_requests:.0f} 的 {pct}%（阈值 +{int(config.spike_ratio * 100)}%）"
        )
        log.warning("traffic anomaly: %s", message)
        return AnomalyResult(
            site_id=baseline.site_id,
            window_sec=baseline.window_sec,
            current_requests=current,
            baseline_avg=baseline.avg_requests,
            deviation_ratio=round(ratio, 3),
            severity=severity,
            message=message,
            detected_at=as_of,
        )
