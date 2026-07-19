from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination, get_current_user
from app.api.listing import (
    ListQuery,
    apply_enabled_filter,
    apply_mode_filter,
    apply_q_filter,
    apply_site_filter,
    get_list_query,
    order_by_fields,
)
from app.core.db import get_db
from app.fields import field_map, validate_condition_with_refs
from app.fields.validator import has_meaningful_conditions
from app.models import RateLimit, User
from app.models.rule import MODES
from app.schemas.common import ok
from app.schemas.rate_limit import RateLimitCreate, RateLimitOut, RateLimitUpdate
from app.services import rule_sync
from app.services.reference_validation import ensure_site_ids_exist
from app.services.site_scope import apply_site_scope, enrich_row

router = APIRouter()
_FIELDS = field_map()


async def _check(db: AsyncSession, mode, keys, conditions):
    resolved_mode = mode if mode is not None else "block"
    if mode is not None and mode not in MODES:
        raise HTTPException(status_code=400, detail=f"无效的防护方式: {mode}")
    if keys is not None and len(keys) < 1:
        raise HTTPException(status_code=400, detail="至少需要配置一个限速维度")
    if keys is not None:
        for k in keys:
            field = k.field if hasattr(k, "field") else k.get("field")
            if field not in _FIELDS:
                raise HTTPException(status_code=400, detail=f"未知限速字段: {field}")
    allow_empty = resolved_mode == "observe"
    if not allow_empty and not has_meaningful_conditions(conditions):
        raise HTTPException(status_code=400, detail="非观察模式必须配置至少一条匹配条件")
    if conditions:
        try:
            return await validate_condition_with_refs(
                db, conditions, allow_empty=allow_empty
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return None


@router.get("")
async def list_items(
    pg: Pagination = Depends(),
    query: ListQuery = Depends(get_list_query),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cond = select(RateLimit)
    count = select(func.count(RateLimit.id))
    cond = apply_q_filter(cond, query.q, RateLimit.name, RateLimit.remark)
    count = apply_q_filter(count, query.q, RateLimit.name, RateLimit.remark)
    cond = apply_enabled_filter(cond, RateLimit.enabled, query.enabled)
    count = apply_enabled_filter(count, RateLimit.enabled, query.enabled)
    cond = apply_mode_filter(cond, RateLimit.mode, query.mode)
    count = apply_mode_filter(count, RateLimit.mode, query.mode)
    cond = apply_site_filter(cond, RateLimit.site_ids, query.site_id)
    count = apply_site_filter(count, RateLimit.site_ids, query.site_id)
    total = (await db.execute(count)).scalar_one()
    cond = order_by_fields(
        cond,
        query.sort_by,
        query.sort_order,
        {
            "name": RateLimit.name,
            "priority": RateLimit.priority,
            "window": RateLimit.window,
            "threshold": RateLimit.threshold,
            "mode": RateLimit.mode,
            "enabled": RateLimit.enabled,
            "id": RateLimit.id,
        },
        RateLimit.priority,
        RateLimit.id,
        tiebreaker=RateLimit.id,
    )
    rows = (
        await db.execute(cond.offset(pg.offset).limit(pg.page_size))
    ).scalars().all()
    return ok({
        "total": total,
        "items": [
            enrich_row(r, RateLimitOut.model_validate(r).model_dump()) for r in rows
        ],
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.get("/{item_id}")
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    item = await db.get(RateLimit, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="限速策略不存在")
    return ok(enrich_row(item, RateLimitOut.model_validate(item).model_dump()))


@router.post("")
async def create_item(
    body: RateLimitCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    normalized = await _check(db, body.mode, body.keys, body.conditions)
    data = apply_site_scope(body.model_dump())
    await ensure_site_ids_exist(db, data.get("site_ids"))
    if normalized is not None:
        data["conditions"] = normalized
    item = RateLimit(**data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await rule_sync.publish(db)
    return ok(enrich_row(item, RateLimitOut.model_validate(item).model_dump()))


@router.put("/{item_id}")
async def update_item(
    item_id: int,
    body: RateLimitUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    item = await db.get(RateLimit, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="限速策略不存在")
    merged_mode = body.mode if body.mode is not None else item.mode
    merged_keys = body.keys if body.keys is not None else item.keys
    merged_conditions = body.conditions if body.conditions is not None else item.conditions
    normalized = await _check(db, merged_mode, merged_keys, merged_conditions)
    patch = apply_site_scope(body.model_dump(exclude_unset=True))
    if "site_ids" in patch:
        await ensure_site_ids_exist(db, patch.get("site_ids"))
    for k, v in patch.items():
        if k == "conditions" and normalized is not None:
            v = normalized
        setattr(item, k, v)
    await db.commit()
    await db.refresh(item)
    await rule_sync.publish(db)
    return ok(enrich_row(item, RateLimitOut.model_validate(item).model_dump()))


@router.delete("/{item_id}")
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    item = await db.get(RateLimit, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="限速策略不存在")
    await db.delete(item)
    await db.commit()
    await rule_sync.publish(db)
    return ok()
