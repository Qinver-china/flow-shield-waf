"""Baseline learning strategies."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.services.traffic_intel.constants import DEFAULT_BASELINE_OUTLIER_QUANTILE
from app.services.traffic_intel.store.clickhouse import ClickHouseTrafficStore
from app.services.traffic_intel.store.baseline_mysql import slot_key_for
from app.services.traffic_intel.timezone import local_datetime
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
        timezone_name: str = "Asia/Shanghai",
    ) -> Baseline | None: ...


class SameSlotHourlyStrategy(BaselineStrategy):
    """Learn median traffic for the same weekday + hour + quarter over lookback days."""

    name = "same_slot_hourly"

    def compute(
        self,
        store: ClickHouseTrafficStore,
        *,
        site_id: int | None,
        window_sec: int,
        config: TrafficIntelConfig,
        as_of: datetime | None = None,
        timezone_name: str = "Asia/Shanghai",
    ) -> Baseline | None:
        as_of = as_of or datetime.utcnow()
        local_as_of = local_datetime(as_of, timezone_name)
        avg_r, samples = store.same_slot_window_averages(
            window_sec,
            site_id=site_id,
            lookback_days=config.baseline_lookback_days,
            as_of=local_as_of,
            timezone_name=timezone_name,
            outlier_quantile=DEFAULT_BASELINE_OUTLIER_QUANTILE,
        )
        if samples < config.min_baseline_samples or avg_r <= 0:
            return None
        return Baseline(
            site_id=site_id,
            window_sec=window_sec,
            avg_requests=avg_r,
            sample_count=samples,
            strategy=self.name,
            slot_key=slot_key_for(local_as_of),
            updated_at=as_of,
        )
