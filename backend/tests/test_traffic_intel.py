"""Tests for traffic anomaly detection math."""
from datetime import datetime

from app.services.traffic_intel.detector.engine import AnomalyDetector
from app.services.traffic_intel.types import Baseline, TrafficIntelConfig


def test_detector_flags_50_percent_spike():
    detector = AnomalyDetector()
    baseline = Baseline(
        site_id=None,
        window_sec=60,
        avg_requests=1000.0,
        sample_count=24,
        strategy="same_slot_hourly",
        slot_key="dow1_h14",
        updated_at=datetime.utcnow(),
    )
    config = TrafficIntelConfig(spike_ratio=0.5)
    result = detector._compare(1600, baseline, config, datetime.utcnow())
    assert result is not None
    assert result.deviation_ratio == 1.6


def test_detector_ignores_normal_traffic():
    detector = AnomalyDetector()
    baseline = Baseline(
        site_id=None,
        window_sec=300,
        avg_requests=5000.0,
        sample_count=30,
        strategy="same_slot_hourly",
        slot_key="dow1_h14",
        updated_at=datetime.utcnow(),
    )
    config = TrafficIntelConfig(spike_ratio=0.5)
    result = detector._compare(7000, baseline, config, datetime.utcnow())
    assert result is None
