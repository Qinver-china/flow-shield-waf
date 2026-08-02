"""Anomaly detection helpers for alert / AI Guard baseline conditions."""
from __future__ import annotations

from datetime import datetime

from app.services.traffic_intel.types import (
    AlertSeverity,
    AnomalyResult,
    Baseline,
    TrafficIntelConfig,
)
from app.services.traffic_intel.windows import label


class AnomalyDetector:
    """Compare live traffic against a learned baseline."""

    def compare(
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
