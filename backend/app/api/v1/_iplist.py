"""Shared CRUD for black/white lists (both back the IpList model)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination, get_current_user
from app.api.listing import (
    ListQuery,
    apply_enabled_filter,
    apply_q_filter,
    apply_site_filter,
    get_list_query,
    order_by_fields,
)
from app.core.db import get_db
from app.fields import validate_condition
from app.models import IpList, User
from app.schemas.common import ok
from app.schemas.ip_list import IpListCreate, IpListOut, IpListUpdate
from app.services import rule_sync
from app.services.site_scope import apply_site_scope, enrich_row


def _validate(conditions: dict | None, *, allow_empty: bool) -> dict | None:
    if conditions is None:
        if not allow_empty:
            raise HTTPException(status_code=400, detail="必须配置至少一条匹配条件")
        return None
    try:
        return validate_condition(conditions, allow_empty=allow_empty)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def make_router(list_type: str) -> APIRouter:
    router = APIRouter()
    allow_empty = list_type != "black"

    @router.get("")
    async def list_items(
        pg: Pagination = Depends(),
        query: ListQuery = Depends(get_list_query),
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
    ):
        cond = select(IpList).where(IpList.list_type == list_type)
        count = select(func.count(IpList.id)).where(IpList.list_type == list_type)
        cond = apply_q_filter(cond, query.q, IpList.name, IpList.remark)
        count = apply_q_filter(count, query.q, IpList.name, IpList.remark)
        cond = apply_enabled_filter(cond, IpList.enabled, query.enabled)
        count = apply_enabled_filter(count, IpList.enabled, query.enabled)
        cond = apply_site_filter(cond, IpList.site_ids, query.site_id)
        count = apply_site_filter(count, IpList.site_ids, query.site_id)
        total = (await db.execute(count)).scalar_one()
        cond = order_by_fields(
            cond,
            query.sort_by,
            query.sort_order,
            {
                "name": IpList.name,
                "enabled": IpList.enabled,
                "id": IpList.id,
            },
            IpList.id,
        )
        rows = (
            await db.execute(cond.offset(pg.offset).limit(pg.page_size))
        ).scalars().all()
        return ok({
            "total": total,
            "items": [
                enrich_row(r, IpListOut.model_validate(r).model_dump()) for r in rows
            ],
            "page": pg.page,
            "page_size": pg.page_size,
        })

    @router.post("")
    async def create_item(
        body: IpListCreate,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
    ):
        normalized = _validate(body.conditions, allow_empty=allow_empty)
        data = apply_site_scope(body.model_dump())
        data["list_type"] = list_type
        data["conditions"] = normalized or {"logic": "and", "conditions": []}
        item = IpList(**data)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        await rule_sync.publish(db)
        return ok(enrich_row(item, IpListOut.model_validate(item).model_dump()))

    @router.put("/{item_id}")
    async def update_item(
        item_id: int,
        body: IpListUpdate,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
    ):
        item = await db.get(IpList, item_id)
        if item is None or item.list_type != list_type:
            raise HTTPException(status_code=404, detail="记录不存在")
        normalized = _validate(body.conditions, allow_empty=allow_empty)
        for k, v in apply_site_scope(body.model_dump(exclude_unset=True)).items():
            if k == "conditions" and normalized is not None:
                v = normalized
            setattr(item, k, v)
        await db.commit()
        await db.refresh(item)
        await rule_sync.publish(db)
        return ok(enrich_row(item, IpListOut.model_validate(item).model_dump()))

    @router.delete("/{item_id}")
    async def delete_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
    ):
        item = await db.get(IpList, item_id)
        if item is None or item.list_type != list_type:
            raise HTTPException(status_code=404, detail="记录不存在")
        await db.delete(item)
        await db.commit()
        await rule_sync.publish(db)
        return ok()

    return router
