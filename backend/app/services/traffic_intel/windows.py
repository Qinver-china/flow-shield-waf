"""Window helpers: labels, validation, and aggregation from minute rollups."""
from __future__ import annotations

from app.constants.traffic_windows import TRAFFIC_BASELINE_WINDOWS_SEC, TRAFFIC_WINDOWS_SEC
from app.services.traffic_intel.constants import WINDOW_LABELS

# Minimum historical buckets to persist a baseline (show on dashboard).
_BASELINE_WARMUP_MIN_SAMPLES: dict[int, int] = {
    60: 3,
    300: 2,
    1800: 1,
    3600: 1,
}

# Minimum buckets before anomaly detection / alerts trust the baseline.
_BASELINE_STABLE_MIN_SAMPLES: dict[int, int] = {
    60: 12,
    300: 9,
    1800: 6,
    3600: 4,
}

_DEFAULT_WARMUP_MIN = 2
_DEFAULT_STABLE_MIN = 12


def label(window_sec: int) -> str:
    return WINDOW_LABELS.get(window_sec, f"{window_sec} 秒")


def validate_analysis_window(window_sec: int) -> int:
    if window_sec not in TRAFFIC_BASELINE_WINDOWS_SEC:
        allowed = ", ".join(str(w) for w in TRAFFIC_BASELINE_WINDOWS_SEC)
        raise ValueError(f"不支持的分析窗口 {window_sec}，可选: {allowed}")
    return window_sec


def validate_traffic_window(window_sec: int) -> int:
    if window_sec not in TRAFFIC_WINDOWS_SEC:
        allowed = ", ".join(str(w) for w in TRAFFIC_WINDOWS_SEC)
        raise ValueError(f"不支持的时间窗口 {window_sec}，可选: {allowed}")
    return window_sec


def minutes_per_window(window_sec: int) -> int:
    """How many 1-minute buckets compose this analysis window."""
    validate_analysis_window(window_sec)
    return max(1, window_sec // 60)


def warmup_min_samples(window_sec: int) -> int:
    """Low bar to learn and display an initial baseline."""
    validate_analysis_window(window_sec)
    return _BASELINE_WARMUP_MIN_SAMPLES.get(window_sec, _DEFAULT_WARMUP_MIN)


def stable_min_samples(window_sec: int) -> int:
    """Higher bar before treating baseline as reliable for alerts."""
    validate_analysis_window(window_sec)
    return _BASELINE_STABLE_MIN_SAMPLES.get(window_sec, _DEFAULT_STABLE_MIN)


def is_baseline_stable(window_sec: int, sample_count: int) -> bool:
    return sample_count >= stable_min_samples(window_sec)
