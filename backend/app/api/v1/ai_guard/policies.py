from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination, get_current_user
from app.core.db import get_db
from app.models import User
from app.models.ai_guard import AiGuardPolicy
from app.models.notification import NotificationChannel
from app.schemas.ai_guard import AiGuardPolicyCreate, AiGuardPolicyOut, AiGuardPolicyUpdate
from app.schemas.common import ok
from app.services.ai_guard.defense.triggers import (
    BLOCK_WINDOWS_MIN,
    TRAFFIC_WINDOWS,
    TRIGGER_TYPES,
    validate_apply_mode,
    validate_trigger_params,
)

router = APIRouter()


@router.get("/meta/triggers")
async def trigger_types(_user: User = Depends(get_current_user)):
    return ok({
        "triggers": TRIGGER_TYPES,
        "traffic_windows": TRAFFIC_WINDOWS,
        "block_windows": BLOCK_WINDOWS_MIN,
    })


@router.get("")
async def list_policies(
    pg: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    total = (await db.execute(select(func.count(AiGuardPolicy.id)))).scalar_one()
    rows = (
        await db.execute(
            select(AiGuardPolicy)
            .order_by(AiGuardPolicy.id.desc())
            .offset(pg.offset)
            .limit(pg.page_size)
        )
    ).scalars().all()
    return ok({
        "total": total,
        "items": [AiGuardPolicyOut.model_validate(r).model_dump() for r in rows],
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.post("")
async def create_policy(
    body: AiGuardPolicyCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        params = validate_trigger_params(body.trigger_type, body.trigger_params)
        apply_mode = validate_apply_mode(body.apply_mode)
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
    custom_prompt = (body.custom_prompt or "").strip() or None
    row = AiGuardPolicy(
        name=body.name,
        enabled=body.enabled,
        trigger_type=body.trigger_type,
        trigger_params=params,
        apply_mode=apply_mode,
        notify_on=body.notify_on,
        channel_ids=body.channel_ids,
        condition_filter=body.condition_filter,
        cooldown_sec=body.cooldown_sec,
        remark=body.remark,
        custom_prompt=custom_prompt,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok(AiGuardPolicyOut.model_validate(row).model_dump())


@router.put("/{policy_id}")
async def update_policy(
    policy_id: int,
    body: AiGuardPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(AiGuardPolicy, policy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="策略不存在")
    data = body.model_dump(exclude_unset=True)
    if "trigger_params" in data or "trigger_type" in data:
        ttype = data.get("trigger_type", row.trigger_type)
        params = data.get("trigger_params", row.trigger_params)
        try:
            data["trigger_params"] = validate_trigger_params(ttype, params)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "apply_mode" in data:
        try:
            data["apply_mode"] = validate_apply_mode(data["apply_mode"])
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
    if "custom_prompt" in data:
        data["custom_prompt"] = (data.get("custom_prompt") or "").strip() or None
    for k, v in data.items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return ok(AiGuardPolicyOut.model_validate(row).model_dump())


@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(AiGuardPolicy, policy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="策略不存在")
    await db.delete(row)
    await db.commit()
    return ok()
