"""Tests for Redis minute-ring timeline bucketing."""
from datetime import datetime, timezone

from app.services.traffic_intel.minute_timeline import build_timeline_points


def test_build_timeline_points_one_minute_buckets():
    end = int(datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc).timestamp())
    requests = {end - 120: 10, end - 60: 20, end: 30}
    origins = {end - 60: 5, end: 15}
    points = build_timeline_points(
        requests,
        origins,
        hours=24,
        bucket_sec=60,
        now_ts=end,
    )
    assert len(points) == 24 * 60
    last = points[-1]
    assert last["ts"] == end
    assert last["requests"] == 30
    assert last["origin_requests"] == 15


def test_build_timeline_points_five_minute_buckets():
    end = int(datetime(2026, 8, 2, 12, 4, tzinfo=timezone.utc).timestamp())
    end -= end % 60
    bucket = end - (end % 300)
    requests = {bucket: 7, bucket + 60: 3, bucket + 120: 5}
    points = build_timeline_points(
        requests,
        {},
        hours=24,
        bucket_sec=300,
        now_ts=end,
    )
    assert points[-1]["requests"] == 15
    assert points[-1]["origin_requests"] == 0
