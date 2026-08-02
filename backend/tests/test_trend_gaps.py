"""Tests for filling missing trend buckets with zeros."""
from datetime import datetime, timedelta, timezone

from app.services.logging.query_clickhouse import _fill_trend_gaps
from app.services.traffic_intel.minute_timeline import iter_timeline_bucket_starts


def test_iter_timeline_bucket_starts_matches_trailing_window():
    end = int(datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc).timestamp())
    starts = iter_timeline_bucket_starts(bucket_sec=600, end_ts=end, hours=24)
    assert len(starts) == 24 * 6
    assert starts[-1] == end


def test_fill_trend_gaps_inserts_zero_buckets():
    end = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)
    start = end - timedelta(hours=24)
    trend = [
        {
            "time": "2026-08-02 06:00:00",
            "count": 3,
            "total": 3,
            "by_mode": {"block": 3},
        }
    ]
    filled = _fill_trend_gaps(
        trend,
        start_ts=start,
        end_ts=end,
        granularity="1h",
    )
    assert len(filled) == 24
    assert filled[0]["count"] == 0
    assert any(point["count"] == 3 for point in filled)
