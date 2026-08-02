"""Traffic timeline chart constants (Redis minute rings)."""

TRAFFIC_TIMELINE_HOURS = 24
TRAFFIC_MINUTE_RETENTION_MINUTES = 25 * 60
TRAFFIC_MINUTE_RETENTION_SEC = TRAFFIC_MINUTE_RETENTION_MINUTES * 60

# Allowed bucket sizes for dashboard timeline (seconds).
TRAFFIC_TIMELINE_BUCKETS_SEC: tuple[int, ...] = (60, 300, 600, 1800, 3600)

TRAFFIC_TIMELINE_BUCKET_LABELS: dict[int, str] = {
    60: "1 分钟",
    300: "5 分钟",
    600: "10 分钟",
    1800: "30 分钟",
    3600: "1 小时",
}

# Dashboard / log stats trend granularity -> bucket seconds (UTC epoch-aligned).
TREND_GRANULARITY_BUCKET_SEC: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "10m": 600,
    "30m": 1800,
    "1h": 3600,
}
