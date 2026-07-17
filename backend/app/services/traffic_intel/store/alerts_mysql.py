"""MySQL persistence for traffic anomaly alerts."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.traffic_intel import TrafficAlert
from app.services.traffic_intel.types import AlertStatus, AnomalyResult


class AlertStore:
    async def create(self, db: AsyncSession, anomaly: AnomalyResult) -> TrafficAlert:
        row = TrafficAlert(
            site_id=anomaly.site_id,
            window_sec=anomaly.window_sec,
            current_requests=anomaly.current_requests,
            baseline_avg=anomaly.baseline_avg,
            deviation_ratio=anomaly.deviation_ratio,
            severity=anomaly.severity.value,
            status=AlertStatus.OPEN.value,
            message=anomaly.message,
            detected_at=anomaly.detected_at,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row

    async def recent_open_count(
        self,
        db: AsyncSession,
        *,
        site_id: int | None,
        window_sec: int,
        within_sec: int,
    ) -> int:
        since = datetime.utcnow() - timedelta(seconds=within_sec)
        stmt = select(func.count(TrafficAlert.id)).where(
            TrafficAlert.site_id == site_id,
            TrafficAlert.window_sec == window_sec,
            TrafficAlert.status == AlertStatus.OPEN.value,
            TrafficAlert.detected_at >= since,
        )
        return int((await db.execute(stmt)).scalar_one())

    async def list_recent(
        self,
        db: AsyncSession,
        *,
        limit: int = 50,
        site_id: int | None = None,
    ) -> list[TrafficAlert]:
        stmt = select(TrafficAlert).order_by(TrafficAlert.detected_at.desc()).limit(limit)
        if site_id is not None:
            stmt = stmt.where(TrafficAlert.site_id == site_id)
        return list((await db.execute(stmt)).scalars().all())
