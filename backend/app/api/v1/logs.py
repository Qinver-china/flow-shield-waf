from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.redis import get_redis
from app.models import User
from app.schemas.common import ok
from app.schemas.log import LogQuery
from app.services.logging.query_clickhouse import (
    STATS_DIMENSIONS,
    get_log,
    query_logs,
    stats_by_dimension,
    stats_overview,
)

router = APIRouter()

VIEWER_KEY = "waf:logs:viewer_active"
VIEWER_TTL = 60


class ViewerHeartbeat(BaseModel):
    active: bool = True


@router.post("/viewer-heartbeat")
async def viewer_heartbeat(
    body: ViewerHeartbeat,
    _user: User = Depends(get_current_user),
):
    redis = get_redis()
    if body.active:
        await redis.set(VIEWER_KEY, "1", ex=VIEWER_TTL)
    else:
        await redis.delete(VIEWER_KEY)
    return ok({"active": body.active, "ttl": VIEWER_TTL})


@router.get("")
async def list_logs(
    q: LogQuery = Depends(),
    _user: User = Depends(get_current_user),
):
    total, items = await query_logs(q)
    rows = []
    for item in items:
        data = dict(item)
        payload = data.pop("payload", None)
        data["has_detail"] = bool(payload)
        rows.append(data)
    return ok({
        "total": total,
        "items": rows,
        "page": q.page,
        "page_size": q.page_size,
    })


@router.get("/stats")
async def logs_stats(
    hours: int = 24,
    start: datetime | None = None,
    end: datetime | None = None,
    _user: User = Depends(get_current_user),
):
    return ok(await stats_overview(hours=hours, start=start, end=end))


@router.get("/stats/group")
async def logs_stats_group(
    dimension: str = Query("rule_id"),
    hours: int = 24,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int | None = Query(None, ge=1, le=100),
    _user: User = Depends(get_current_user),
):
    if dimension not in STATS_DIMENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的统计维度，可选: {', '.join(sorted(STATS_DIMENSIONS))}",
        )
    effective_page_size = limit if limit is not None else page_size
    try:
        data = await stats_by_dimension(
            dimension=dimension,
            hours=hours,
            start=start,
            end=end,
            page=page,
            page_size=effective_page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(data.model_dump())


@router.get("/{log_id}")
async def get_log_detail(
    log_id: str,
    _user: User = Depends(get_current_user),
):
    row = await get_log(log_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Log not found")
    return ok(row)
