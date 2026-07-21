"""Shared traffic window definitions (engine counters + rule conditions)."""

# Rule DSL / alert condition windows (no 24h — too coarse for most rules).
TRAFFIC_WINDOWS_SEC: tuple[int, ...] = (10, 30, 60, 300, 1800, 3600)

# Live counters + dashboard snapshot (includes 24h). Keep in sync with traffic_counter.lua.
TRAFFIC_LIVE_WINDOWS_SEC: tuple[int, ...] = (10, 30, 60, 300, 1800, 3600, 86400)

# Windows used for baseline learning / anomaly comparison (no 10s / 30s / 24h).
TRAFFIC_BASELINE_WINDOWS_SEC: tuple[int, ...] = (60, 300, 1800, 3600)

# Minimum window for baseline-relative rule / alert comparisons.
TRAFFIC_BASELINE_MIN_WINDOW_SEC = 300

TRAFFIC_WINDOW_LABELS: dict[int, str] = {
    10: "10 秒",
    30: "30 秒",
    60: "1 分钟",
    300: "5 分钟",
    1800: "30 分钟",
    3600: "60 分钟",
    86400: "24 小时",
}


def traffic_window_options(*, as_string: bool = False) -> list[dict]:
    out: list[dict] = []
    for sec in TRAFFIC_WINDOWS_SEC:
        label = TRAFFIC_WINDOW_LABELS.get(sec, f"{sec} 秒")
        out.append({"value": str(sec) if as_string else sec, "label": label})
    return out
