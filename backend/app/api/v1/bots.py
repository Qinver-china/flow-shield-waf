from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.api.deps import Pagination, get_current_user
from app.api.listing import ListQuery, get_list_query, order_by_fields
from app.core.db import get_db
from app.models import BotProfile, User
from app.schemas.bot import BotProfileCreate, BotProfileOut, BotProfileUpdate
from app.schemas.common import ok
from app.services import rule_sync
from app.services.bot_catalog import ensure_categories_exist, normalize_patterns
from app.services.reference_validation import ensure_site_ids_exist
from app.services.site_scope import apply_site_scope, enrich_row

router = APIRouter()


def _out(row: BotProfile) -> dict:
    data = BotProfileOut.model_validate(row).model_dump()
    data["pattern_count"] = len(row.ua_patterns or [])
    return data


def _apply_bot_q(stmt: Select, q: str | None) -> Select:
    if not q:
        return stmt
    pattern = f"%{q}%"
    patterns_text = cast(BotProfile.ua_patterns, String)
    return stmt.where(
        or_(
            BotProfile.name.like(pattern),
            BotProfile.remark.like(pattern),
            patterns_text.like(pattern),
        )
    )


def _apply_category_filter(stmt: Select, categories: list[str] | None) -> Select:
    if not categories:
        return stmt
    values = [c.strip() for c in categories if c and c.strip()]
    if not values:
        return stmt
    clauses = [cast(BotProfile.categories, String).like(f'%"{v}"%') for v in values]
    return stmt.where(or_(*clauses))


@router.get("/vendored")
async def get_vendored_info(
    _user: User = Depends(get_current_user),
):
    from app.services.crawler_vendored import manifest_for_api

    return ok(manifest_for_api())


@router.post("/vendored/sync")
async def sync_vendored_rules(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    from app.services.crawler_vendored.sync import sync_from_upstream

    try:
        result = await sync_from_upstream(db, force=True, source="manual")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"更新 vendored 规则失败: {exc}") from exc
    return ok(result)


@router.get("")
async def list_bots(
    pg: Pagination = Depends(),
    query: ListQuery = Depends(get_list_query),
    category: list[str] | None = Query(None, description="Bot 分类，可多选"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cond = select(BotProfile)
    count = select(func.count(BotProfile.id))
    cond = _apply_bot_q(cond, query.q)
    count = _apply_bot_q(count, query.q)
    cond = _apply_category_filter(cond, category)
    count = _apply_category_filter(count, category)
    total = (await db.execute(count)).scalar_one()
    cond = order_by_fields(
        cond,
        query.sort_by,
        query.sort_order,
        {
            "name": BotProfile.name,
            "id": BotProfile.id,
        },
        BotProfile.id,
    )
    rows = (await db.execute(cond.offset(pg.offset).limit(pg.page_size))).scalars().all()
    return ok({
        "total": total,
        "items": [_out(r) for r in rows],
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.get("/{bot_id}")
async def get_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(BotProfile, bot_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bot 不存在")
    return ok(_out(row))


@router.post("")
async def create_bot(
    body: BotProfileCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    await ensure_site_ids_exist(db, body.site_ids)
    try:
        categories = await ensure_categories_exist(db, body.categories)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    data = apply_site_scope(body.model_dump())
    row = BotProfile(
        name=data["name"],
        categories=categories,
        ua_patterns=data["ua_patterns"],
        enabled=True,
        site_ids=data.get("site_ids"),
        verify_dns_suffix=data.get("verify_dns_suffix"),
        remark=data.get("remark"),
        is_builtin=False,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(enrich_row(row, _out(row)))


@router.put("/{bot_id}")
async def update_bot(
    bot_id: int,
    body: BotProfileUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(BotProfile, bot_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bot 不存在")
    data = body.model_dump(exclude_unset=True)
    if "site_ids" in data:
        await ensure_site_ids_exist(db, data["site_ids"])
        data = apply_site_scope(data)
    if "categories" in data:
        try:
            data["categories"] = await ensure_categories_exist(db, data["categories"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "ua_patterns" in data:
        data["ua_patterns"] = normalize_patterns(data["ua_patterns"])
    for key, value in data.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(enrich_row(row, _out(row)))


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(BotProfile, bot_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bot 不存在")
    await db.delete(row)
    await db.commit()
    await rule_sync.publish(db)
    return ok()
