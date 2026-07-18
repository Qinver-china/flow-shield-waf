"""Window helpers: labels, validation, and aggregation from minute rollups."""
from __future__ import annotations

from app.constants.traffic_windows import TRAFFIC_BASELINE_WINDOWS_SEC, TRAFFIC_WINDOWS_SEC
from app.services.traffic_intel.constants import WINDOW_LABELS


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
