"""MySQL persistence for learned baselines."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.traffic_intel import TrafficBaseline
from app.services.traffic_intel.types import Baseline
from app.services.traffic_intel.timezone import local_datetime


def slot_key_for(as_of: datetime) -> str:
    """Same weekday + hour + 15-minute quarter in local wall-clock time."""
    quarter = as_of.minute // 15
    return f"dow{as_of.isoweekday()}_h{as_of.hour}_q{quarter}"


class BaselineStore:
    async def upsert(
        self,
        db: AsyncSession,
        baseline: Baseline,
    ) -> TrafficBaseline:
        row = (
            await db.execute(
                select(TrafficBaseline).where(
                    TrafficBaseline.site_id == baseline.site_id,
                    TrafficBaseline.window_sec == baseline.window_sec,
                    TrafficBaseline.slot_key == baseline.slot_key,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = TrafficBaseline(
                site_id=baseline.site_id,
                window_sec=baseline.window_sec,
                slot_key=baseline.slot_key,
                strategy=baseline.strategy,
            )
            db.add(row)
        row.avg_requests = baseline.avg_requests
        row.sample_count = baseline.sample_count
        row.updated_at = baseline.updated_at
        await db.commit()
        await db.refresh(row)
        return row

    async def get(
        self,
        db: AsyncSession,
        *,
        site_id: int | None,
        window_sec: int,
        as_of: datetime | None = None,
        timezone_name: str | None = None,
    ) -> Baseline | None:
        as_of = as_of or datetime.utcnow()
        local_as_of = (
            local_datetime(as_of, timezone_name)
            if timezone_name
            else as_of
        )
        slot_key = slot_key_for(local_as_of)
        row = (
            await db.execute(
                select(TrafficBaseline).where(
                    TrafficBaseline.site_id == site_id,
                    TrafficBaseline.window_sec == window_sec,
                    TrafficBaseline.slot_key == slot_key,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return Baseline(
            site_id=row.site_id,
            window_sec=row.window_sec,
            avg_requests=float(row.avg_requests),
            sample_count=int(row.sample_count),
            strategy=row.strategy,
            slot_key=row.slot_key,
            updated_at=row.updated_at or datetime.utcnow(),
        )

    async def list_all(
        self,
        db: AsyncSession,
        *,
        site_id: int | None = None,
    ) -> list[Baseline]:
        stmt = select(TrafficBaseline)
        if site_id is not None:
            stmt = stmt.where(TrafficBaseline.site_id == site_id)
        rows = (await db.execute(stmt.order_by(TrafficBaseline.window_sec))).scalars().all()
        return [
            Baseline(
                site_id=r.site_id,
                window_sec=r.window_sec,
                avg_requests=float(r.avg_requests),
                sample_count=int(r.sample_count),
                strategy=r.strategy,
                slot_key=r.slot_key,
                updated_at=r.updated_at or datetime.utcnow(),
            )
            for r in rows
        ]
