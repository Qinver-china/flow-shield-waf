from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.models.notification import AlertPolicy, NotificationChannel
from app.schemas.common import ok
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelOut,
    NotificationChannelUpdate,
)
from app.services.notifications.channels import mask_channel_config, send_via_channel, validate_channel_config
from app.services.notifications.email_templates import build_test_email

router = APIRouter()

PASSWORD_MASK = "******"


def _out(row: NotificationChannel) -> dict:
    data = NotificationChannelOut.model_validate(row).model_dump()
    data["config_masked"] = mask_channel_config(row.channel_type, row.config or {})
    if row.channel_type == "email" and data.get("config"):
        data["config"] = dict(data["config_masked"])
    return data


@router.get("")
async def list_channels(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(select(NotificationChannel).order_by(NotificationChannel.id.desc()))
    ).scalars().all()
    return ok([_out(r) for r in rows])


@router.post("")
async def create_channel(
    body: NotificationChannelCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        config = validate_channel_config(body.channel_type, body.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = NotificationChannel(
        name=body.name,
        channel_type=body.channel_type,
        enabled=body.enabled,
        config=config,
        remark=body.remark,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok(_out(row))


@router.put("/{channel_id}")
async def update_channel(
    channel_id: int,
    body: NotificationChannelUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(NotificationChannel, channel_id)
    if row is None:
        raise HTTPException(status_code=404, detail="通知通道不存在")
    data = body.model_dump(exclude_unset=True)
    if "config" in data and data["config"] is not None:
        merged = dict(row.config or {})
        incoming = data["config"]
        if row.channel_type == "email" and incoming.get("smtp_password") in (None, "", PASSWORD_MASK):
            incoming = {**incoming, "smtp_password": merged.get("smtp_password", "")}
        merged.update(incoming)
        try:
            data["config"] = validate_channel_config(row.channel_type, merged)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    for k, v in data.items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return ok(_out(row))


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(NotificationChannel, channel_id)
    if row is None:
        raise HTTPException(status_code=404, detail="通知通道不存在")
    policies = (
        await db.execute(select(AlertPolicy))
    ).scalars().all()
    for policy in policies:
        if channel_id in (policy.channel_ids or []):
            raise HTTPException(
                status_code=400,
                detail=f"通知通道正在被预警规则「{policy.name}」引用，无法删除",
            )
    await db.delete(row)
    await db.commit()
    return ok()


@router.post("/{channel_id}/test")
async def test_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(NotificationChannel, channel_id)
    if row is None:
        raise HTTPException(status_code=404, detail="通知通道不存在")
    try:
        plain, html_body = build_test_email()
        await send_via_channel(
            row,
            subject="流盾WAF 通知通道测试",
            body=plain,
            html_body=html_body,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok({"sent": True})
