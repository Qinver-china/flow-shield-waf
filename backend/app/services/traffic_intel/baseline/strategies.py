"""Baseline learning strategies."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.services.traffic_intel.constants import DEFAULT_BASELINE_OUTLIER_QUANTILE
from app.services.traffic_intel.store.clickhouse import ClickHouseTrafficStore
from app.services.traffic_intel.store.baseline_mysql import slot_key_for
from app.services.traffic_intel.timezone import local_datetime
from app.services.traffic_intel.types import Baseline, TrafficIntelConfig
from app.services.traffic_intel.windows import warmup_min_samples

# Lightweight daily alignment (no weekday):
# - short windows: 15-minute quarter within the hour, then hour
# - long windows: hour only (quarter would chop 30m/60m semantics)
_SLOT_FALLBACK_SHORT: tuple[tuple[str, str], ...] = (
    ("same_tod_quarter", "quarter"),
    ("same_tod_hour", "hour"),
)
_SLOT_FALLBACK_LONG: tuple[tuple[str, str], ...] = (
    ("same_tod_hour", "hour"),
)


def _slot_chain_for_window(window_sec: int) -> tuple[tuple[str, str], ...]:
    if window_sec >= 1800:
        return _SLOT_FALLBACK_LONG
    return _SLOT_FALLBACK_SHORT


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
    """Learn median of window-snapshot readings for the same time-of-day."""

    name = "same_tod"

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
        warmup_min = warmup_min_samples(window_sec)

        for strategy_name, slot_mode in _slot_chain_for_window(window_sec):
            avg_r, samples = store.same_slot_window_averages(
                window_sec,
                site_id=site_id,
                lookback_days=config.baseline_lookback_days,
                as_of_utc=as_of,
                timezone_name=timezone_name,
                slot_mode=slot_mode,
                outlier_quantile=DEFAULT_BASELINE_OUTLIER_QUANTILE,
            )
            if samples < warmup_min or avg_r <= 0:
                continue
            return Baseline(
                site_id=site_id,
                window_sec=window_sec,
                avg_requests=avg_r,
                sample_count=samples,
                strategy=strategy_name,
                slot_key=slot_key_for(local_as_of),
                updated_at=as_of,
            )
        return None
