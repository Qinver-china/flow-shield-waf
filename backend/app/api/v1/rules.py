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
from app.fields import validate_condition_with_refs
from app.models import Rule, User
from app.models.rule import MODES
from app.schemas.common import ok
from app.schemas.rule import RuleCreate, RuleOut, RuleUpdate
from app.services import rule_sync
from app.services.reference_validation import ensure_site_ids_exist
from app.services.site_scope import apply_site_scope, enrich_row

router = APIRouter()


async def _check(
    db: AsyncSession,
    mode: str | None,
    conditions: dict | None,
    *,
    effective_mode: str | None = None,
) -> dict | None:
    if mode is not None and mode not in MODES:
        raise HTTPException(status_code=400, detail=f"无效的防护方式: {mode}")
    resolved_mode = mode if mode is not None else effective_mode
    allow_empty = resolved_mode == "observe"
    if conditions is not None:
        try:
            return await validate_condition_with_refs(db, conditions, allow_empty=allow_empty)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return None


@router.get("")
async def list_rules(
    pg: Pagination = Depends(),
    query: ListQuery = Depends(get_list_query),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cond = select(Rule)
    count = select(func.count(Rule.id))
    cond = apply_q_filter(cond, query.q, Rule.name, Rule.remark)
    count = apply_q_filter(count, query.q, Rule.name, Rule.remark)
    cond = apply_enabled_filter(cond, Rule.enabled, query.enabled)
    count = apply_enabled_filter(count, Rule.enabled, query.enabled)
    cond = apply_mode_filter(cond, Rule.mode, query.mode)
    count = apply_mode_filter(count, Rule.mode, query.mode)
    cond = apply_site_filter(cond, Rule.site_ids, query.site_id)
    count = apply_site_filter(count, Rule.site_ids, query.site_id)
    total = (await db.execute(count)).scalar_one()
    cond = order_by_fields(
        cond,
        query.sort_by,
        query.sort_order,
        {
            "name": Rule.name,
            "priority": Rule.priority,
            "mode": Rule.mode,
            "enabled": Rule.enabled,
            "id": Rule.id,
        },
        Rule.priority,
        Rule.id,
        tiebreaker=Rule.id,
    )
    rows = (
        await db.execute(cond.offset(pg.offset).limit(pg.page_size))
    ).scalars().all()
    return ok({
        "total": total,
        "items": [
            enrich_row(r, RuleOut.model_validate(r).model_dump()) for r in rows
        ],
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.get("/{rule_id}")
async def get_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rule = await db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    return ok(enrich_row(rule, RuleOut.model_validate(rule).model_dump()))


@router.post("")
async def create_rule(
    body: RuleCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    normalized = await _check(db, body.mode, body.conditions)
    data = apply_site_scope(body.model_dump())
    await ensure_site_ids_exist(db, data.get("site_ids"))
    data["conditions"] = normalized or {"logic": "and", "conditions": []}
    rule = Rule(**data)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    await rule_sync.publish(db)
    return ok(enrich_row(rule, RuleOut.model_validate(rule).model_dump()))


@router.put("/{rule_id}")
async def update_rule(
    rule_id: int,
    body: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rule = await db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    normalized = await _check(db, body.mode, body.conditions, effective_mode=rule.mode)
    patch = apply_site_scope(body.model_dump(exclude_unset=True))
    if "site_ids" in patch:
        await ensure_site_ids_exist(db, patch.get("site_ids"))
    for k, v in patch.items():
        if k == "conditions" and normalized is not None:
            v = normalized
        setattr(rule, k, v)
    await db.commit()
    await db.refresh(rule)
    await rule_sync.publish(db)
    return ok(enrich_row(rule, RuleOut.model_validate(rule).model_dump()))


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rule = await db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    await db.delete(rule)
    await db.commit()
    await rule_sync.publish(db)
    return ok()
