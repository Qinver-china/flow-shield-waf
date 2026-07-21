"""Unit tests for defense traffic overview helpers."""
from __future__ import annotations

from app.services.ai_guard.defense.traffic_context import _pick_primary_requests, _window_rows
from app.services.traffic_intel.types import WindowSample


def test_window_rows_compute_qps_from_requests():
    rows = _window_rows([
        WindowSample(window_sec=60, requests=120, qps=0.0),
        WindowSample(window_sec=300, requests=900, qps=3.0),
    ])
    by_sec = {r["window_sec"]: r for r in rows}
    assert by_sec[60]["requests"] == 120
    assert by_sec[60]["qps"] == 2.0
    assert by_sec[300]["qps"] == 3.0
    assert by_sec[60]["label"] == "1 分钟"


def test_pick_primary_requests_prefers_focus_window():
    windows = [
        {"window_sec": 60, "requests": 10},
        {"window_sec": 300, "requests": 99},
    ]
    assert _pick_primary_requests(windows, 300) == 99
    assert _pick_primary_requests(windows, None) == 10
