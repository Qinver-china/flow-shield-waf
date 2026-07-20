from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination, get_current_user
from app.constants.alert_conditions import ALERT_CONDITION_TYPES, CHANNEL_TYPES
from app.core.db import get_db
from app.models import User
from app.models.notification import AlertPolicy, NotificationChannel
from app.services.analytics.alert_log_store import AlertLogStore
from app.schemas.common import ok
from app.schemas.notification import AlertPolicyCreate, AlertPolicyOut, AlertPolicyUpdate
from app.services.notifications.validators import validate_condition_params
from app.services.notifications.evaluator import latest_dispatch_status_by_policy

router = APIRouter()


@router.get("/meta/conditions")
async def alert_condition_types(_user: User = Depends(get_current_user)):
    from app.constants.alert_conditions import TRAFFIC_WINDOWS

    return ok({
        "conditions": ALERT_CONDITION_TYPES,
        "channel_types": CHANNEL_TYPES,
        "traffic_windows": TRAFFIC_WINDOWS,
    })


@router.get("")
async def list_policies(
    pg: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    total = (await db.execute(select(func.count(AlertPolicy.id)))).scalar_one()
    rows = (
        await db.execute(
            select(AlertPolicy)
            .order_by(AlertPolicy.id.desc())
            .offset(pg.offset)
            .limit(pg.page_size)
        )
    ).scalars().all()
    status_map = await latest_dispatch_status_by_policy(db, [r.id for r in rows])
    items = []
    for row in rows:
        data = AlertPolicyOut.model_validate(row).model_dump()
        data["last_dispatch_status"] = status_map.get(row.id)
        items.append(data)
    return ok({
        "total": total,
        "items": items,
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.post("")
async def create_policy(
    body: AlertPolicyCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        params = validate_condition_params(body.condition_type, body.condition_params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if body.channel_ids:
        cnt = (
            await db.execute(
                select(func.count(NotificationChannel.id)).where(
                    NotificationChannel.id.in_(body.channel_ids)
                )
            )
        ).scalar_one()
        if cnt != len(body.channel_ids):
            raise HTTPException(status_code=400, detail="部分通知通道不存在")
    row = AlertPolicy(
        name=body.name,
        enabled=body.enabled,
        condition_type=body.condition_type,
        condition_params=params,
        channel_ids=body.channel_ids,
        cooldown_sec=body.cooldown_sec,
        remark=body.remark,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok(AlertPolicyOut.model_validate(row).model_dump())


@router.put("/{policy_id}")
async def update_policy(
    policy_id: int,
    body: AlertPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(AlertPolicy, policy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="预警规则不存在")
    data = body.model_dump(exclude_unset=True)
    ctype = data.get("condition_type", row.condition_type)
    if "condition_params" in data or "condition_type" in data:
        params = data.get("condition_params", row.condition_params)
        try:
            data["condition_params"] = validate_condition_params(ctype, params)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "channel_ids" in data and data["channel_ids"]:
        cnt = (
            await db.execute(
                select(func.count(NotificationChannel.id)).where(
                    NotificationChannel.id.in_(data["channel_ids"])
                )
            )
        ).scalar_one()
        if cnt != len(data["channel_ids"]):
            raise HTTPException(status_code=400, detail="部分通知通道不存在")
    for k, v in data.items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return ok(AlertPolicyOut.model_validate(row).model_dump())


@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(AlertPolicy, policy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="预警规则不存在")
    await db.delete(row)
    await db.commit()
    return ok()


@router.get("/logs")
async def list_notification_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = await AlertLogStore().list_recent(limit=min(limit, 200))
    return ok([
        {
            "id": r.id,
            "policy_id": r.policy_id,
            "channel_id": r.channel_id,
            "status": r.status,
            "message": r.message,
            "detail": r.detail,
            "created_at": r.created_at,
        }
        for r in rows
    ])
