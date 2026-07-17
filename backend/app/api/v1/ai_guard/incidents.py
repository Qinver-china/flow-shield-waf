from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination, get_current_user
from app.core.db import get_db
from app.models import User
from app.models.ai_guard import AiGuardIncident
from app.schemas.ai_guard import AiGuardIncidentOut, ApplyIncidentRequest
from app.schemas.common import ok
from app.services.ai_guard.defense.pipeline import (
    apply_incident_rule,
    rollback_incident,
)

router = APIRouter()


@router.get("")
async def list_incidents(
    pg: Pagination = Depends(),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cond = select(AiGuardIncident)
    count = select(func.count(AiGuardIncident.id))
    if status:
        cond = cond.where(AiGuardIncident.status == status)
        count = count.where(AiGuardIncident.status == status)
    total = (await db.execute(count)).scalar_one()
    rows = (
        await db.execute(
            cond.order_by(AiGuardIncident.id.desc()).offset(pg.offset).limit(pg.page_size)
        )
    ).scalars().all()
    return ok({
        "total": total,
        "items": [AiGuardIncidentOut.model_validate(r).model_dump() for r in rows],
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.get("/{incident_id}")
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(AiGuardIncident, incident_id)
    if row is None:
        raise HTTPException(status_code=404, detail="事件不存在")
    return ok(AiGuardIncidentOut.model_validate(row).model_dump())


@router.post("/{incident_id}/apply")
async def apply_incident(
    incident_id: int,
    body: ApplyIncidentRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        row = await apply_incident_rule(
            db, incident_id, apply_mode=body.apply_mode
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(AiGuardIncidentOut.model_validate(row).model_dump())


@router.post("/{incident_id}/dismiss")
async def dismiss_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(AiGuardIncident, incident_id)
    if row is None:
        raise HTTPException(status_code=404, detail="事件不存在")
    row.status = "dismissed"
    await db.commit()
    return ok()


@router.post("/{incident_id}/rollback")
async def rollback_incident_rule(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        row = await rollback_incident(db, incident_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(AiGuardIncidentOut.model_validate(row).model_dump())
