from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination, get_current_user
from app.api.listing import (
    ListQuery,
    apply_enabled_filter,
    apply_q_filter,
    apply_scope_filter,
    apply_site_filter,
    get_list_query,
    order_by_fields,
)
from app.core.db import get_db
from app.fields import validate_condition
from app.models import Exception_, User
from app.models.exception import SCOPES
from app.schemas.common import ok
from app.schemas.exception import ExceptionCreate, ExceptionOut, ExceptionUpdate
from app.services import rule_sync
from app.services.reference_validation import ensure_site_ids_exist
from app.services.site_scope import apply_site_scope, enrich_row

router = APIRouter()


def _check(
    scope: str | None,
    conditions: dict | None,
    *,
    require_conditions: bool = False,
) -> dict | None:
    if scope is not None and scope not in SCOPES:
        raise HTTPException(status_code=400, detail=f"无效的例外范围: {scope}")
    allow_empty = not require_conditions
    if conditions is None:
        if require_conditions:
            raise HTTPException(
                status_code=400,
                detail="跳过全部防护时必须配置至少一条匹配条件",
            )
        return None
    try:
        return validate_condition(conditions, allow_empty=allow_empty)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
async def list_items(
    pg: Pagination = Depends(),
    query: ListQuery = Depends(get_list_query),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cond = select(Exception_)
    count = select(func.count(Exception_.id))
    cond = apply_q_filter(cond, query.q, Exception_.name, Exception_.remark)
    count = apply_q_filter(count, query.q, Exception_.name, Exception_.remark)
    cond = apply_enabled_filter(cond, Exception_.enabled, query.enabled)
    count = apply_enabled_filter(count, Exception_.enabled, query.enabled)
    cond = apply_scope_filter(cond, Exception_.scope, query.scope)
    count = apply_scope_filter(count, Exception_.scope, query.scope)
    cond = apply_site_filter(cond, Exception_.site_ids, query.site_id)
    count = apply_site_filter(count, Exception_.site_ids, query.site_id)
    total = (await db.execute(count)).scalar_one()
    cond = order_by_fields(
        cond,
        query.sort_by,
        query.sort_order,
        {
            "name": Exception_.name,
            "scope": Exception_.scope,
            "enabled": Exception_.enabled,
            "id": Exception_.id,
        },
        Exception_.id,
    )
    rows = (
        await db.execute(cond.offset(pg.offset).limit(pg.page_size))
    ).scalars().all()
    return ok({
        "total": total,
        "items": [
            enrich_row(r, ExceptionOut.model_validate(r).model_dump()) for r in rows
        ],
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.post("")
async def create_item(
    body: ExceptionCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    require = (body.scope or "all") == "all"
    normalized = _check(body.scope, body.conditions, require_conditions=require)
    data = apply_site_scope(body.model_dump())
    await ensure_site_ids_exist(db, data.get("site_ids"))
    data["conditions"] = normalized or {"logic": "and", "conditions": []}
    item = Exception_(**data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await rule_sync.publish(db)
    return ok(enrich_row(item, ExceptionOut.model_validate(item).model_dump()))


@router.put("/{item_id}")
async def update_item(
    item_id: int,
    body: ExceptionUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    item = await db.get(Exception_, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="例外不存在")
    patch = body.model_dump(exclude_unset=True)
    scope = patch.get("scope", item.scope)
    scoped = apply_site_scope(patch)
    if "site_ids" in scoped:
        await ensure_site_ids_exist(db, scoped.get("site_ids"))
    if "conditions" in patch or scope == "all":
        conditions = patch["conditions"] if "conditions" in patch else item.conditions
        normalized = _check(scope, conditions, require_conditions=(scope == "all"))
    else:
        normalized = None
    for k, v in scoped.items():
        if k == "conditions" and normalized is not None:
            v = normalized
        setattr(item, k, v)
    await db.commit()
    await db.refresh(item)
    await rule_sync.publish(db)
    return ok(enrich_row(item, ExceptionOut.model_validate(item).model_dump()))


@router.delete("/{item_id}")
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    item = await db.get(Exception_, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="例外不存在")
    await db.delete(item)
    await db.commit()
    await rule_sync.publish(db)
    return ok()
