"""Tests for traffic baseline slot keys and timezone helpers."""
from datetime import datetime

from app.services.traffic_intel.store.baseline_mysql import slot_key_for
from app.services.traffic_intel.timezone import local_datetime
from app.services.traffic_intel.windows import (
    is_baseline_stable,
    stable_min_samples,
    warmup_min_samples,
)


def test_slot_key_is_time_of_day_only():
    dt = datetime(2026, 7, 18, 14, 37)
    assert slot_key_for(dt) == "h14_q2"
    # Same clock time on another weekday shares the key (no dow).
    other = datetime(2026, 7, 20, 14, 37)
    assert slot_key_for(other) == "h14_q2"


def test_local_datetime_from_utc():
    utc = datetime(2026, 7, 18, 6, 30)
    local = local_datetime(utc, "Asia/Shanghai")
    assert local.hour == 14
    assert local.minute == 30


def test_warmup_thresholds_are_lower_than_stable():
    for window_sec in (60, 300, 1800, 3600):
        assert warmup_min_samples(window_sec) < stable_min_samples(window_sec)


def test_baseline_stable_requires_more_samples_for_short_windows():
    assert not is_baseline_stable(60, warmup_min_samples(60))
    assert is_baseline_stable(60, stable_min_samples(60))
    assert is_baseline_stable(3600, warmup_min_samples(3600))

