"""MySQL persistence for learned baselines."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.traffic_intel import TrafficBaseline
from app.services.traffic_intel.types import Baseline
from app.services.traffic_intel.timezone import local_datetime


def slot_key_for(as_of: datetime) -> str:
    """Time-of-day slot in local wall-clock time (no weekday).

    Lightweight baseline key: same hour + 15-minute quarter every day.
    Example: 14:37 → ``h14_q2``.
    """
    quarter = as_of.minute // 15
    return f"h{as_of.hour}_q{quarter}"


def _row_to_baseline(row: TrafficBaseline) -> Baseline:
    return Baseline(
        site_id=row.site_id,
        window_sec=row.window_sec,
        avg_requests=float(row.avg_requests),
        sample_count=int(row.sample_count),
        strategy=row.strategy,
        slot_key=row.slot_key,
        updated_at=row.updated_at or datetime.utcnow(),
    )


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

    async def _latest_site_row(
        self,
        db: AsyncSession,
        *,
        site_id: int,
        window_sec: int,
        prefer_slot: str | None = None,
    ) -> TrafficBaseline | None:
        """Prefer the current slot row; otherwise the most recently updated one."""
        if prefer_slot:
            row = (
                await db.execute(
                    select(TrafficBaseline).where(
                        TrafficBaseline.site_id == site_id,
                        TrafficBaseline.window_sec == window_sec,
                        TrafficBaseline.slot_key == prefer_slot,
                    )
                )
            ).scalar_one_or_none()
            if row is not None:
                return row
        return (
            await db.execute(
                select(TrafficBaseline)
                .where(
                    TrafficBaseline.site_id == site_id,
                    TrafficBaseline.window_sec == window_sec,
                )
                .order_by(TrafficBaseline.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

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

        # Global view: sum per-site baselines (current slot, else latest).
        if site_id is None:
            site_ids = (
                await db.execute(
                    select(TrafficBaseline.site_id)
                    .where(
                        TrafficBaseline.site_id.is_not(None),
                        TrafficBaseline.window_sec == window_sec,
                    )
                    .distinct()
                )
            ).scalars().all()
            picked: list[TrafficBaseline] = []
            for sid in site_ids:
                if sid is None:
                    continue
                row = await self._latest_site_row(
                    db, site_id=int(sid), window_sec=window_sec, prefer_slot=slot_key
                )
                if row is not None:
                    picked.append(row)
            if not picked:
                return None
            total_avg = sum(float(r.avg_requests) for r in picked)
            min_samples = min(int(r.sample_count) for r in picked)
            return Baseline(
                site_id=None,
                window_sec=window_sec,
                avg_requests=total_avg,
                sample_count=min_samples,
                strategy="sum_sites",
                slot_key=slot_key,
                updated_at=max(
                    (r.updated_at for r in picked if r.updated_at),
                    default=datetime.utcnow(),
                ),
            )

        row = await self._latest_site_row(
            db, site_id=int(site_id), window_sec=window_sec, prefer_slot=slot_key
        )
        if row is None:
            return None
        return _row_to_baseline(row)

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
        return [_row_to_baseline(r) for r in rows]
