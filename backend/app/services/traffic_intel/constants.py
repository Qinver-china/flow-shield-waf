"""Traffic intelligence constants.

Realtime windows (engine) vs analysis windows (baseline / anomaly detection):
- Engine keeps 10s–24h sliding counters for dashboard + burst logging.
- Intel baseline learning focuses on 1m / 5m / 30m / 60m.
"""

from app.constants.traffic_windows import (
    TRAFFIC_BASELINE_WINDOWS_SEC,
    TRAFFIC_LIVE_WINDOWS_SEC,
    TRAFFIC_WINDOW_LABELS as WINDOW_LABELS,
)

# Live engine windows including 24h.
REALTIME_WINDOWS_SEC = TRAFFIC_LIVE_WINDOWS_SEC

# Windows used for baseline learning (subset of live windows).
ANALYSIS_WINDOWS_SEC = TRAFFIC_BASELINE_WINDOWS_SEC

REDIS_SNAPSHOT_KEY = "waf:traffic:snapshot"

# Default anomaly: current > baseline * (1 + SPIKE_RATIO)  →  50% above average.
DEFAULT_SPIKE_RATIO = 0.5
DEFAULT_BASELINE_LOOKBACK_DAYS = 28
# Disk TTL for traffic history: lookback (28d) + ~7d buffer; MergeTree auto-expires.
TRAFFIC_HISTORY_TTL_DAYS = 35
# Legacy global floor; per-window thresholds live in windows.warmup_min_samples / stable_min_samples.
DEFAULT_MIN_BASELINE_SAMPLES = 12
DEFAULT_BASELINE_OUTLIER_QUANTILE = 0.99
DEFAULT_ALERT_COOLDOWN_SEC = 300
DEFAULT_INGEST_INTERVAL_SEC = 60
DEFAULT_BASELINE_RECALC_INTERVAL_SEC = 900

# ClickHouse
CH_MINUTE_TABLE = "traffic_minute"
CH_WINDOW_SNAPSHOT_TABLE = "traffic_window_snapshot"
