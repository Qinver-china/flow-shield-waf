"""In-memory ring buffer + Redis publisher for system metric windows."""
from __future__ import annotations

import json
import logging
import time
from collections import deque
from typing import Any

from app.constants.system_metrics import (
    REDIS_SYSTEM_METRICS_KEY,
    SYSTEM_METRIC_WINDOWS_SEC,
    SYSTEM_METRICS_SAMPLE_INTERVAL_SEC,
)
from app.core.redis import get_redis
from app.services.system_metrics.sampler import CpuSample, SystemMetricsSampler

log = logging.getLogger("waf.system_metrics")

_METRIC_KEYS = (
    "container_cpu_pct",
    "host_cpu_pct",
)


class SystemMetricsCollector:
    """Collect samples and publish 1/5/30-minute averages to Redis."""

    def __init__(self) -> None:
        self._sampler = SystemMetricsSampler()
        max_samples = int(max(SYSTEM_METRIC_WINDOWS_SEC) / SYSTEM_METRICS_SAMPLE_INTERVAL_SEC) + 12
        self._ring: deque[CpuSample] = deque(maxlen=max_samples)

    def tick(self) -> dict[str, Any]:
        sample = self._sampler.sample()
        self._ring.append(sample)
        return self.build_snapshot(sample)

    def build_snapshot(self, latest: CpuSample | None = None) -> dict[str, Any]:
        latest = latest or (self._ring[-1] if self._ring else None)
        now = time.time()
        windows: dict[str, Any] = {}
        for window_sec in SYSTEM_METRIC_WINDOWS_SEC:
            windows[str(window_sec)] = self._avg_window(now, window_sec)

        instant = {
            "container_cpu_pct": latest.container_cpu_pct if latest else None,
            "host_cpu_pct": latest.host_cpu_pct if latest else None,
            "cpu_cores": latest.cpu_cores if latest else None,
            "source": latest.source if latest else "unavailable",
        }
        return {
            "updated_at": int(now),
            "sample_interval_sec": SYSTEM_METRICS_SAMPLE_INTERVAL_SEC,
            "instant": instant,
            "windows": windows,
        }

    def _avg_window(self, now: float, window_sec: int) -> dict[str, Any]:
        cutoff = now - window_sec
        rows = [s for s in self._ring if s.ts >= cutoff]
        out: dict[str, Any] = {"samples": len(rows)}
        for key in _METRIC_KEYS:
            vals = [getattr(s, key) for s in rows if getattr(s, key) is not None]
            out[f"{key}_avg"] = round(sum(vals) / len(vals), 3) if vals else None
        return out

    async def publish(self, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = snapshot or self.build_snapshot()
        try:
            redis = get_redis()
            await redis.set(
                REDIS_SYSTEM_METRICS_KEY,
                json.dumps(payload, ensure_ascii=False),
                ex=max(SYSTEM_METRIC_WINDOWS_SEC) * 2,
            )
        except Exception:  # noqa: BLE001
            log.exception("failed to publish system metrics snapshot")
        return payload


_collector: SystemMetricsCollector | None = None


def get_collector() -> SystemMetricsCollector:
    global _collector
    if _collector is None:
        _collector = SystemMetricsCollector()
    return _collector


async def read_system_metrics_snapshot() -> dict[str, Any] | None:
    """Load the latest published metrics snapshot from Redis."""
    try:
        raw = await get_redis().get(REDIS_SYSTEM_METRICS_KEY)
    except Exception:  # noqa: BLE001
        log.exception("failed to read system metrics snapshot")
        return None
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def window_metric_value(
    snapshot: dict[str, Any] | None,
    *,
    window_sec: int,
    metric: str,
) -> float | None:
    """Read a window average metric from a snapshot."""
    if not snapshot:
        return None
    windows = snapshot.get("windows") or {}
    row = windows.get(str(int(window_sec))) or {}
    key = metric if str(metric).endswith("_avg") else f"{metric}_avg"
    val = row.get(key)
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None
