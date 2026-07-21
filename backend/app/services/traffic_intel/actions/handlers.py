"""Action handlers invoked when an anomaly is detected."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.traffic_intel.store.alerts_clickhouse import AlertStore
from app.services.traffic_intel.types import AnomalyResult, TrafficIntelConfig

log = logging.getLogger("waf.traffic_intel.actions")


class ActionHandler(ABC):
    @abstractmethod
    async def handle(
        self,
        db: AsyncSession,
        anomaly: AnomalyResult,
        config: TrafficIntelConfig,
    ) -> None: ...


class PersistAlertHandler(ActionHandler):
    """Always record anomalies in ClickHouse."""

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
    """Structured log for external notification integrations (webhook/email later)."""

    async def handle(
        self,
        db: AsyncSession,
        anomaly: AnomalyResult,
        config: TrafficIntelConfig,
    ) -> None:
        # Persisted via PersistAlertHandler; keep container logs quiet at WARNING+.
        log.info(
            "TRAFFIC_ALERT site=%s window=%ss severity=%s ratio=%.2f msg=%s",
            anomaly.site_id,
            anomaly.window_sec,
            anomaly.severity.value,
            anomaly.deviation_ratio,
            anomaly.message,
        )


class ActionDispatcher:
    def __init__(self, handlers: list[ActionHandler] | None = None):
        if handlers is None:
            from app.services.ai_guard.traffic_handler import AiGuardTrafficHandler

            handlers = [
                PersistAlertHandler(),
                LogNotifyHandler(),
                AiGuardTrafficHandler(),
            ]
        self._handlers = handlers

    async def dispatch(
        self,
        db: AsyncSession,
        anomalies: list[AnomalyResult],
        config: TrafficIntelConfig,
    ) -> None:
        for anomaly in anomalies:
            for handler in self._handlers:
                await handler.handle(db, anomaly, config)
