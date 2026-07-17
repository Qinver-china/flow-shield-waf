"""Baseline learning strategies."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.services.traffic_intel.store.clickhouse import ClickHouseTrafficStore
from app.services.traffic_intel.types import Baseline, TrafficIntelConfig


class BaselineStrategy(ABC):
    name: str

    @abstractmethod
    def compute(
        self,
        store: ClickHouseTrafficStore,
        *,
        site_id: int | None,
        window_sec: int,
        config: TrafficIntelConfig,
        as_of: datetime | None = None,
    ) -> Baseline | None: ...


class SameSlotHourlyStrategy(BaselineStrategy):
    """Learn average traffic for the same weekday + hour slot over lookback days."""

    name = "same_slot_hourly"

    def compute(
        self,
        store: ClickHouseTrafficStore,
        *,
        site_id: int | None,
        window_sec: int,
        config: TrafficIntelConfig,
        as_of: datetime | None = None,
    ) -> Baseline | None:
        as_of = as_of or datetime.utcnow()
        avg_r, samples = store.same_slot_window_averages(
            window_sec,
            site_id=site_id,
            lookback_days=config.baseline_lookback_days,
            as_of=as_of,
        )
        if samples < config.min_baseline_samples or avg_r <= 0:
            return None
        return Baseline(
            site_id=site_id,
            window_sec=window_sec,
            avg_requests=avg_r,
            sample_count=samples,
            strategy=self.name,
            slot_key=f"dow{as_of.isoweekday()}_h{as_of.hour}",
            updated_at=as_of,
        )
