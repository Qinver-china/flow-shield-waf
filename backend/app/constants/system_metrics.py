"""System CPU metric windows shared by rules, alerts, and AI triggers."""

# Rolling averages published by the worker (seconds).
SYSTEM_METRIC_WINDOWS_SEC: tuple[int, ...] = (60, 300, 1800)

SYSTEM_METRIC_WINDOW_LABELS: dict[int, str] = {
    60: "1 分钟",
    300: "5 分钟",
    1800: "30 分钟",
}

REDIS_SYSTEM_METRICS_KEY = "waf:system:metrics"

# Sample period for the background collector.
SYSTEM_METRICS_SAMPLE_INTERVAL_SEC = 5

# Skip sampling right after process start — boot spike would skew window averages.
SYSTEM_METRICS_STARTUP_DELAY_SEC = 60


def system_metric_window_options(*, as_string: bool = False) -> list[dict]:
    out: list[dict] = []
    for sec in SYSTEM_METRIC_WINDOWS_SEC:
        label = SYSTEM_METRIC_WINDOW_LABELS.get(sec, f"{sec} 秒")
        out.append({"value": str(sec) if as_string else sec, "label": label})
    return out
