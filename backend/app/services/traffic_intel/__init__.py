"""Traffic intelligence framework.

Layers
------
1. **采集 (ingest)** — read engine Redis snapshot, persist minute + window history to ClickHouse.
2. **基线 (baseline)** — learn same-slot median (weekday + hour + quarter) per global/site.
3. **检测 (detector)** — flag spikes when current > baseline × (1 + spike_ratio).
4. **动作 (actions)** — persist alerts, log/notify (extend with webhooks).

Extend
------
- Add per-site scopes: extend engine snapshot + pass site_ids into pipeline.
- Swap baseline strategy in ``baseline/strategies.py``.
- Register custom handlers on ``ActionDispatcher``.
"""
from app.services.traffic_intel.baseline import BaselineCalculator, SameSlotHourlyStrategy
from app.services.traffic_intel.constants import ANALYSIS_WINDOWS_SEC, REALTIME_WINDOWS_SEC
from app.services.traffic_intel.detector import AnomalyDetector
from app.services.traffic_intel.ingest import SnapshotIngestor, parse_snapshot
from app.services.traffic_intel.pipeline import TrafficIntelPipeline, run_pipeline_loop
from app.services.traffic_intel.types import (
    AlertSeverity,
    AnomalyResult,
    Baseline,
    TrafficIntelConfig,
    TrafficSnapshot,
    WindowSample,
)

__all__ = [
    "ANALYSIS_WINDOWS_SEC",
    "REALTIME_WINDOWS_SEC",
    "AlertSeverity",
    "AnomalyResult",
    "Baseline",
    "BaselineCalculator",
    "AnomalyDetector",
    "SameSlotHourlyStrategy",
    "SnapshotIngestor",
    "TrafficIntelConfig",
    "TrafficIntelPipeline",
    "TrafficSnapshot",
    "WindowSample",
    "parse_snapshot",
    "run_pipeline_loop",
]
