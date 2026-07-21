import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.constants.traffic_windows import TRAFFIC_BASELINE_WINDOWS_SEC, TRAFFIC_WINDOWS_SEC
from app.core.db import get_db
from app.core.redis import get_redis
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
    DEFAULT_BASELINE_LOOKBACK_DAYS,
    DEFAULT_SPIKE_RATIO,
    REDIS_SNAPSHOT_KEY,
)
from app.services.traffic_intel.store.alerts_clickhouse import AlertStore
from app.services.traffic_intel.store.baseline_mysql import BaselineStore
from app.services.traffic_intel.store.clickhouse import ClickHouseTrafficStore
from app.services.traffic_intel.types import TrafficIntelConfig
from app.services.traffic_intel.timezone import get_traffic_timezone
from app.services.traffic_intel.windows import is_baseline_stable, label

router = APIRouter()


def _config() -> TrafficIntelConfig:
    return TrafficIntelConfig(
        spike_ratio=DEFAULT_SPIKE_RATIO,
        baseline_lookback_days=DEFAULT_BASELINE_LOOKBACK_DAYS,
    )


def _snapshot_window_requests(raw: str | bytes | None, window_sec: int, site_id: int | None) -> int | None:
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    if site_id is None:
        windows = data.get("global", {}).get("windows") or []
    else:
        site_data = (data.get("sites") or {}).get(str(site_id), {})
        windows = site_data.get("windows") or []

    for w in windows:
        try:
            if int(w.get("sec", 0)) == window_sec:
                return int(w.get("requests") or 0)
        except (TypeError, ValueError):
            continue
    return None


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
    rows = await AlertStore().list_recent(limit=limit, site_id=site_id)
    return ok([
        AlertOut(
            id=r.id,
            site_id=r.site_id,
            window_sec=r.window_sec,
            current_requests=r.current_requests,
            baseline_avg=r.baseline_avg,
            deviation_ratio=r.deviation_ratio,
            severity=r.severity,
            status=r.status,
            message=r.message,
            detected_at=r.detected_at,
        )
        for r in rows
    ])


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
    snapshot_raw = await get_redis().get(REDIS_SNAPSHOT_KEY)

    windows: list[WindowComparison] = []
    for window_sec in TRAFFIC_WINDOWS_SEC:
        baseline = None
        if window_sec in TRAFFIC_BASELINE_WINDOWS_SEC:
            baseline = await baselines.get(
                db,
                site_id=site_id,
                window_sec=window_sec,
                as_of=datetime.utcnow(),
                timezone_name=timezone_name,
            )

        current = _snapshot_window_requests(snapshot_raw, window_sec, site_id)
        if current is None and window_sec in TRAFFIC_BASELINE_WINDOWS_SEC:
            current = ch.current_window_requests(window_sec, site_id=site_id)
        if current is None:
            current = 0

        baseline_avg = baseline.avg_requests if baseline else None
        baseline_sample_count = baseline.sample_count if baseline else None
        baseline_warmup = bool(
            baseline is not None
            and baseline_avg is not None
            and not is_baseline_stable(window_sec, baseline.sample_count)
        )
        ratio = (current / baseline_avg) if baseline_avg and baseline_avg > 0 else None
        windows.append(
            WindowComparison(
                window_sec=window_sec,
                label=label(window_sec),
                current_requests=current,
                baseline_avg=baseline_avg,
                baseline_sample_count=baseline_sample_count,
                baseline_warmup=baseline_warmup,
                deviation_ratio=round(ratio, 3) if ratio is not None else None,
                spike_threshold_ratio=config.spike_ratio,
                is_anomaly=False,
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
