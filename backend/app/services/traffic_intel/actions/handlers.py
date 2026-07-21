"""Action handlers for traffic anomalies (kept for tests / optional wiring).

Built-in auto-alerting is disabled; the traffic intel pipeline no longer
dispatches these handlers. Alert / AI Guard policies use ``traffic.baseline_*``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.traffic_intel.store.alerts_clickhouse import AlertStore
from app.services.traffic_intel.types import AnomalyResult, TrafficIntelConfig


class ActionHandler(ABC):
    @abstractmethod
    async def handle(
        self,
        db: AsyncSession,
        anomaly: AnomalyResult,
        config: TrafficIntelConfig,
    ) -> None: ...


class PersistAlertHandler(ActionHandler):
    """Record anomalies in ClickHouse (unused by default pipeline)."""

    def __init__(self, store: AlertStore | None = None):
        self._store = store or AlertStore()

    async def handle(
        self,
        db: AsyncSession,
        anomaly: AnomalyResult,
        config: TrafficIntelConfig,
    ) -> None:
        await self._store.create(anomaly)


class LogNotifyHandler(ActionHandler):
    """No-op stub retained for import compatibility."""

    async def handle(
        self,
        db: AsyncSession,
        anomaly: AnomalyResult,
        config: TrafficIntelConfig,
    ) -> None:
        return


class ActionDispatcher:
    def __init__(self, handlers: list[ActionHandler] | None = None):
        self._handlers = handlers or []

    async def dispatch(
        self,
        db: AsyncSession,
        anomalies: list[AnomalyResult],
        config: TrafficIntelConfig,
    ) -> None:
        for anomaly in anomalies:
            for handler in self._handlers:
                await handler.handle(db, anomaly, config)
