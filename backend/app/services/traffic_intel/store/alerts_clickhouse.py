"""ClickHouse persistence for traffic anomaly alerts."""
from __future__ import annotations

from app.services.analytics.traffic_alert_store import TrafficAlertRecord, TrafficAlertStore
from app.services.traffic_intel.types import AnomalyResult

_store = TrafficAlertStore()


class AlertStore:
    async def create(self, anomaly: AnomalyResult) -> TrafficAlertRecord:
        return await _store.create(anomaly)

    async def recent_open_count(
        self,
        *,
        site_id: int | None,
        window_sec: int,
        within_sec: int,
    ) -> int:
        return await _store.recent_open_count(
            site_id=site_id,
            window_sec=window_sec,
            within_sec=within_sec,
        )

    async def list_recent(
        self,
        *,
        limit: int = 50,
        site_id: int | None = None,
    ) -> list[TrafficAlertRecord]:
        return await _store.list_recent(limit=limit, site_id=site_id)
