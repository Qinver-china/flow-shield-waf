"""Read host/container CPU usage from Linux proc/cgroup."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CpuSample:
    """One instantaneous sample of CPU metrics."""

    ts: float
    container_cpu_pct: float | None
    host_cpu_pct: float | None
    cpu_cores: int
    source: str


@dataclass
class _CpuCounters:
    container_usage_ns: int | None
    host_busy_ns: int | None
    host_total_ns: int | None
    monotonic: float


def _cpu_cores() -> int:
    n = os.cpu_count() or 1
    return max(1, int(n))


_CACHED_CORES: int | None = None


def _cached_cpu_cores() -> int:
    global _CACHED_CORES
    if _CACHED_CORES is None:
        _CACHED_CORES = _cpu_cores()
    return _CACHED_CORES


def _read_cgroup_usage_ns() -> tuple[int | None, str]:
    """Return (usage_nanoseconds, source_label)."""
    # cgroup v2 — only need the usage_usec line
    v2 = Path("/sys/fs/cgroup/cpu.stat")
    if v2.is_file():
        try:
            with v2.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("usage_usec"):
                        usec = int(line.split()[1])
                        return usec * 1000, "cgroup_v2"
        except (OSError, IndexError, ValueError):
            pass

    # cgroup v1
    for path in (
        Path("/sys/fs/cgroup/cpuacct/cpuacct.usage"),
        Path("/sys/fs/cgroup/cpu,cpuacct/cpuacct.usage"),
    ):
        if path.is_file():
            try:
                return int(path.read_text(encoding="utf-8").strip()), "cgroup_v1"
            except (OSError, ValueError):
                continue
    return None, "unavailable"


def _read_host_stat_ns() -> tuple[int | None, int | None]:
    """Return (busy_ns, total_ns) from /proc/stat first cpu line (jiffies → ns)."""
    try:
        hz = os.sysconf(os.sysconf_names.get("SC_CLK_TCK", "SC_CLK_TCK"))
    except (ValueError, OSError, AttributeError):
        hz = 100
    hz = max(1, int(hz))
    try:
        with open("/proc/stat", encoding="utf-8") as fh:
            line = fh.readline()
        parts = line.split()
        if not parts or parts[0] != "cpu":
            return None, None
        vals = [int(x) for x in parts[1:8]]
        # user nice system idle iowait irq softirq
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        total = sum(vals)
        busy = total - idle
        scale = 1_000_000_000 // hz
        return busy * scale, total * scale
    except (OSError, ValueError, IndexError):
        return None, None


def _read_counters() -> tuple[_CpuCounters, str]:
    container_ns, source = _read_cgroup_usage_ns()
    host_busy, host_total = _read_host_stat_ns()
    return (
        _CpuCounters(
            container_usage_ns=container_ns,
            host_busy_ns=host_busy,
            host_total_ns=host_total,
            monotonic=time.monotonic(),
        ),
        source,
    )


class SystemMetricsSampler:
    """Delta-based CPU% sampler (needs two ticks before percentages are valid)."""

    def __init__(self) -> None:
        self._prev: _CpuCounters | None = None
        self._source = "unavailable"

    def sample(self) -> CpuSample:
        cores = _cached_cpu_cores()
        counters, source = _read_counters()
        self._source = source

        container_pct: float | None = None
        host_pct: float | None = None
        prev = self._prev
        self._prev = counters

        if prev is not None:
            dt = counters.monotonic - prev.monotonic
            if dt > 0 and counters.container_usage_ns is not None and prev.container_usage_ns is not None:
                delta = counters.container_usage_ns - prev.container_usage_ns
                if delta >= 0:
                    # usage over wall time → percent of one core (may exceed 100 on multi-core)
                    container_pct = max(0.0, min(100.0 * cores, (delta / (dt * 1_000_000_000)) * 100.0))
            if (
                dt > 0
                and counters.host_busy_ns is not None
                and prev.host_busy_ns is not None
                and counters.host_total_ns is not None
                and prev.host_total_ns is not None
            ):
                dbusy = counters.host_busy_ns - prev.host_busy_ns
                dtotal = counters.host_total_ns - prev.host_total_ns
                if dtotal > 0 and dbusy >= 0:
                    host_pct = max(0.0, min(100.0, (dbusy / dtotal) * 100.0))

        return CpuSample(
            ts=time.time(),
            container_cpu_pct=round(container_pct, 3) if container_pct is not None else None,
            host_cpu_pct=round(host_pct, 3) if host_pct is not None else None,
            cpu_cores=cores,
            source=source if container_pct is not None else (
                "host_only" if host_pct is not None else "unavailable"
            ),
        )
