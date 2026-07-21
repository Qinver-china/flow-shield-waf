"""Tests for system CPU sampling windows and condition validation."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app.fields import validate_condition
from app.fields.catalog import catalog_for_frontend, catalog_compact_for_llm
from app.services.notifications.validators import validate_condition_params
from app.services.system_metrics.collector import SystemMetricsCollector, window_metric_value
from app.services.system_metrics.sampler import CpuSample


def _sample(**kwargs) -> CpuSample:
    base = dict(
        ts=time.time(),
        container_cpu_pct=40.0,
        host_cpu_pct=50.0,
        cpu_cores=4,
        source="cgroup_v2",
    )
    base.update(kwargs)
    return CpuSample(**base)


def test_collector_window_averages():
    collector = SystemMetricsCollector()
    now = time.time()
    with patch.object(collector._sampler, "sample") as sample_fn:
        sample_fn.side_effect = [
            _sample(ts=now - 20, container_cpu_pct=20.0, host_cpu_pct=10.0),
            _sample(ts=now - 10, container_cpu_pct=40.0, host_cpu_pct=20.0),
            _sample(ts=now - 1, container_cpu_pct=60.0, host_cpu_pct=30.0),
        ]
        for _ in range(3):
            snap = collector.tick()

    win = snap["windows"]["60"]
    assert win["samples"] == 3
    assert win["container_cpu_pct_avg"] == 40.0
    assert win["host_cpu_pct_avg"] == 20.0
    assert "loadavg_1_avg" not in win


def test_window_metric_value_reads_avg_key():
    snapshot = {
        "windows": {
            "300": {"container_cpu_pct_avg": 81.5, "samples": 10},
        }
    }
    assert window_metric_value(snapshot, window_sec=300, metric="container_cpu_pct") == 81.5
    assert window_metric_value(snapshot, window_sec=60, metric="container_cpu_pct") is None


def test_system_cpu_condition_ok():
    cond = validate_condition({
        "field": "system.cpu",
        "op": "compare",
        "value": {"window_sec": 300, "compare": "container_cpu_gt", "threshold": 80},
    })
    assert cond["conditions"][0]["field"] == "system.cpu"


def test_system_cpu_load_compare_rejected():
    with pytest.raises(ValueError):
        validate_condition({
            "field": "system.cpu",
            "op": "compare",
            "value": {"window_sec": 60, "compare": "load_gt", "threshold": 4},
        })


def test_system_cpu_invalid_window_rejected():
    with pytest.raises(ValueError):
        validate_condition({
            "field": "system.cpu",
            "op": "compare",
            "value": {"window_sec": 120, "compare": "host_cpu_gt", "threshold": 90},
        })


def test_system_cpu_in_frontend_catalog():
    cat = catalog_for_frontend()
    fields = {f["key"]: f for c in cat["categories"] for f in c["fields"]}
    modes = {m["value"] for m in fields["system.cpu"]["compare_modes"]}
    assert modes == {"container_cpu_gt", "container_cpu_lt", "host_cpu_gt", "host_cpu_lt"}
    assert len(fields["system.cpu"]["options"]) == 3


def test_catalog_compact_includes_system_value():
    catalog = catalog_compact_for_llm()
    assert catalog["system_value"]["value"]["window_sec"] == [60, 300, 1800]
    fields = {item["key"]: item for item in catalog["fields"]}
    assert "container_cpu_gt" in fields["system.cpu"]["compare_modes"]
    assert "load_gt" not in fields["system.cpu"]["compare_modes"]


def test_alert_system_params_ok():
    params = validate_condition_params(
        "system.container_cpu_gt",
        {"window_sec": 300, "threshold": 80},
    )
    assert params["window_sec"] == 300
    assert params["threshold"] == 80.0


def test_alert_system_params_bad_window():
    with pytest.raises(ValueError):
        validate_condition_params(
            "system.host_cpu_gt",
            {"window_sec": 120, "threshold": 90},
        )
