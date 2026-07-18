"""Shared types for the traffic intelligence framework."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class AlertSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class TrafficIntelConfig:
    """Runtime configuration for the intel pipeline."""

    enabled: bool = True
    spike_ratio: float = 0.5
    baseline_lookback_days: int = 28
    min_baseline_samples: int = 12
    alert_cooldown_sec: int = 300
    analysis_windows_sec: tuple[int, ...] = (60, 300, 1800, 3600)


@dataclass(frozen=True)
class WindowSample:
    """A single window measurement at a point in time."""

    window_sec: int
    requests: int
    qps: float = 0.0
    site_id: int | None = None
    observed_at: datetime | None = None


@dataclass(frozen=True)
class TrafficSnapshot:
    """Parsed Redis snapshot from the engine."""

    updated_at: int
    global_windows: list[WindowSample] = field(default_factory=list)
    burst_active: bool = False
    site_windows: dict[int, list[WindowSample]] = field(default_factory=dict)


@dataclass(frozen=True)
class Baseline:
    """Learned normal traffic level for a scope + window."""

    site_id: int | None
    window_sec: int
    avg_requests: float
    sample_count: int
    strategy: str
    slot_key: str
    updated_at: datetime


@dataclass(frozen=True)
class AnomalyResult:
    """Outcome when current traffic exceeds learned baseline."""

    site_id: int | None
    window_sec: int
    current_requests: int
    baseline_avg: float
    deviation_ratio: float
    severity: AlertSeverity
    message: str
    detected_at: datetime
