"""Tests for traffic baseline slot keys and timezone helpers."""
from datetime import datetime

from app.services.traffic_intel.store.baseline_mysql import slot_key_for
from app.services.traffic_intel.timezone import local_datetime


def test_slot_key_includes_quarter():
    dt = datetime(2026, 7, 18, 14, 37)
    assert slot_key_for(dt) == "dow6_h14_q2"


def test_local_datetime_from_utc():
    utc = datetime(2026, 7, 18, 6, 30)
    local = local_datetime(utc, "Asia/Shanghai")
    assert local.hour == 14
    assert local.minute == 30
