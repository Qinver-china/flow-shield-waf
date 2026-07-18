"""Default logging / traffic auto-enable settings."""

from app.constants.traffic_windows import TRAFFIC_WINDOWS_SEC

DEFAULT_LOGGING_CONTROL_MODE = "manual"
DEFAULT_LOGGING_ENABLED = True
DEFAULT_LOGGING_SKIP_OBSERVE = False
DEFAULT_OBSERVE_SAMPLE_RATE_IDLE = 0.01
DEFAULT_OBSERVE_SAMPLE_RATE_ACTIVE = 1.0
DEFAULT_LOGGING_DETAIL_ON_BLOCK = True
DEFAULT_LOGGING_AUTO_COOLDOWN_SEC = 120
DEFAULT_LOGGING_AUTO_OBSERVE_SAMPLE_RATE = 1.0
DEFAULT_LOG_RETENTION_DAYS = 30

DEFAULT_AUTO_THRESHOLDS: list[dict] = [
    {"window_sec": 60, "max_requests": 2000},
    {"window_sec": 300, "max_requests": 8000},
    {"window_sec": 1800, "max_requests": 40000},
    {"window_sec": 3600, "max_requests": 80000},
]

TRAFFIC_WINDOWS = list(TRAFFIC_WINDOWS_SEC)
