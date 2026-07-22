"""Recompute and persist traffic baselines."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.traffic_intel.baseline.strategies import SameSlotHourlyStrategy
from app.services.traffic_intel.store.baseline_mysql import BaselineStore
from app.services.traffic_intel.store.clickhouse import ClickHouseTrafficStore
from app.services.traffic_intel.types import Baseline, TrafficIntelConfig

log = logging.getLogger("waf.traffic_intel.baseline")


class BaselineCalculator:
    def __init__(
        self,
        ch_store: ClickHouseTrafficStore | None = None,
        mysql_store: BaselineStore | None = None,
        strategy: SameSlotHourlyStrategy | None = None,
    ):
        self._ch = ch_store or ClickHouseTrafficStore()
        self._mysql = mysql_store or BaselineStore()
        self._strategy = strategy or SameSlotHourlyStrategy()

    async def recalculate(
        self,
        db: AsyncSession,
        config: TrafficIntelConfig,
        *,
        site_ids: list[int | None] | None = None,
        as_of: datetime | None = None,
        timezone_name: str | None = None,
    ) -> list[Baseline]:
        from app.services.traffic_intel.timezone import get_traffic_timezone

        if timezone_name is None:
            timezone_name = await get_traffic_timezone(db)
        scopes = site_ids if site_ids is not None else []
        saved: list[Baseline] = []
        for site_id in scopes:
            if site_id is None:
                continue
            for window_sec in config.analysis_windows_sec:
                baseline = await asyncio.to_thread(
                    self._strategy.compute,
                    self._ch,
                    site_id=site_id,
                    window_sec=window_sec,
                    config=config,
                    as_of=as_of,
                    timezone_name=timezone_name,
                )
                if baseline is None:
                    log.debug(
                        "skip baseline site=%s window=%ss (insufficient samples)",
                        site_id,
                        window_sec,
                    )
                    continue
                await self._mysql.upsert(db, baseline)
                saved.append(baseline)
                log.info(
                    "baseline updated site=%s window=%ss avg=%.1f samples=%d",
                    site_id,
                    window_sec,
                    baseline.avg_requests,
                    baseline.sample_count,
                )
        return saved
