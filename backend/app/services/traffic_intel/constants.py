"""Traffic intelligence constants.

Realtime windows (engine) vs analysis windows (baseline / anomaly detection):
- Engine keeps 1m–60m sliding counters for dashboard + burst logging.
- Intel pipeline uses the same windows for baseline comparison and attack hints.
"""

from app.constants.traffic_windows import TRAFFIC_BASELINE_WINDOWS_SEC, TRAFFIC_WINDOWS_SEC

# Windows published by engine (traffic_counter.lua) — keep in sync with Lua WINDOWS.
REALTIME_WINDOWS_SEC = TRAFFIC_WINDOWS_SEC

# Windows used for baseline + anomaly detection.
ANALYSIS_WINDOWS_SEC = TRAFFIC_BASELINE_WINDOWS_SEC

from app.constants.traffic_windows import TRAFFIC_WINDOW_LABELS as WINDOW_LABELS

REDIS_SNAPSHOT_KEY = "waf:traffic:snapshot"

# Default anomaly: current > baseline * (1 + SPIKE_RATIO)  →  50% above average.
DEFAULT_SPIKE_RATIO = 0.5
DEFAULT_BASELINE_LOOKBACK_DAYS = 28
DEFAULT_MIN_BASELINE_SAMPLES = 12
DEFAULT_BASELINE_OUTLIER_QUANTILE = 0.95
DEFAULT_ALERT_COOLDOWN_SEC = 300
DEFAULT_INGEST_INTERVAL_SEC = 60
DEFAULT_BASELINE_RECALC_INTERVAL_SEC = 3600

# ClickHouse
CH_MINUTE_TABLE = "traffic_minute"
CH_WINDOW_SNAPSHOT_TABLE = "traffic_window_snapshot"
