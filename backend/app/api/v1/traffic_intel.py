from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.common import ok
from app.schemas.traffic_intel import (
    AlertOut,
    BaselineOut,
    IntelStatusOut,
    MinuteSeriesPoint,
    WindowComparison,
)
from app.services.traffic_intel.constants import (
    ANALYSIS_WINDOWS_SEC,
    DEFAULT_BASELINE_LOOKBACK_DAYS,
    DEFAULT_SPIKE_RATIO,
)
from app.services.traffic_intel.store.alerts_mysql import AlertStore
from app.services.traffic_intel.store.baseline_mysql import BaselineStore
from app.services.traffic_intel.store.clickhouse import ClickHouseTrafficStore
from app.services.traffic_intel.types import TrafficIntelConfig
from app.services.traffic_intel.timezone import get_traffic_timezone
from app.services.traffic_intel.windows import label

router = APIRouter()


def _config() -> TrafficIntelConfig:
    return TrafficIntelConfig(
        spike_ratio=DEFAULT_SPIKE_RATIO,
        baseline_lookback_days=DEFAULT_BASELINE_LOOKBACK_DAYS,
    )


@router.get("/baselines")
async def list_baselines(
    site_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = await BaselineStore().list_all(db, site_id=site_id)
    return ok([
        BaselineOut(
            site_id=r.site_id,
            window_sec=r.window_sec,
            slot_key=r.slot_key,
            strategy=r.strategy,
            avg_requests=r.avg_requests,
            sample_count=r.sample_count,
            updated_at=r.updated_at,
        )
        for r in rows
    ])


@router.get("/alerts")
async def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    site_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = await AlertStore().list_recent(db, limit=limit, site_id=site_id)
    return ok([AlertOut.model_validate(r) for r in rows])


@router.get("/series")
async def minute_series(
    hours: int = Query(24, ge=1, le=168),
    site_id: int | None = None,
    _user: User = Depends(get_current_user),
):
    store = ClickHouseTrafficStore()
    points = store.recent_minute_series(site_id=site_id, hours=hours)
    return ok([
        MinuteSeriesPoint(minute=p["minute"], requests=p["requests"]) for p in points
    ])


@router.get("/status")
async def intel_status(
    site_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    config = _config()
    ch = ClickHouseTrafficStore()
    baselines = BaselineStore()
    timezone_name = await get_traffic_timezone(db)

    windows: list[WindowComparison] = []
    for window_sec in ANALYSIS_WINDOWS_SEC:
        baseline = await baselines.get(
            db,
            site_id=site_id,
            window_sec=window_sec,
            as_of=datetime.utcnow(),
            timezone_name=timezone_name,
        )
        current = ch.current_window_requests(window_sec, site_id=site_id)
        baseline_avg = baseline.avg_requests if baseline else None
        ratio = (current / baseline_avg) if baseline_avg and baseline_avg > 0 else None
        threshold = (
            baseline_avg * (1 + config.spike_ratio)
            if baseline_avg and baseline_avg > 0
            else None
        )
        windows.append(
            WindowComparison(
                window_sec=window_sec,
                label=label(window_sec),
                current_requests=current,
                baseline_avg=baseline_avg,
                deviation_ratio=round(ratio, 3) if ratio is not None else None,
                spike_threshold_ratio=config.spike_ratio,
                is_anomaly=bool(threshold is not None and current > threshold),
            )
        )

    return ok(
        IntelStatusOut(
            site_id=site_id,
            spike_ratio=config.spike_ratio,
            baseline_lookback_days=config.baseline_lookback_days,
            windows=windows,
        )
    )
