from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.api.deps import Pagination, get_current_user
from app.api.listing import ListQuery, get_list_query, order_by_fields
from app.constants.bot_settings import RESERVED_CATEGORY_OTHER
from app.core.db import get_db
from app.models import BotCategory, BotProfile, User
from app.schemas.bot_category import (
    BotCategoryCreate,
    BotCategoryOption,
    BotCategoryOut,
    BotCategoryUpdate,
)
from app.schemas.common import ok
from app.services import rule_sync
from app.services.reference_validation import find_bot_category_references

router = APIRouter()


def _out(row: BotCategory) -> dict:
    return BotCategoryOut.model_validate(row).model_dump()


def _apply_q(stmt: Select, q: str | None) -> Select:
    if not q:
        return stmt
    pattern = f"%{q}%"
    return stmt.where(
        or_(
            BotCategory.value.like(pattern),
            BotCategory.label.like(pattern),
            BotCategory.remark.like(pattern),
        )
    )


@router.get("")
async def list_bot_categories(
    pg: Pagination = Depends(),
    query: ListQuery = Depends(get_list_query),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cond = select(BotCategory)
    count = select(func.count(BotCategory.id))
    cond = _apply_q(cond, query.q)
    count = _apply_q(count, query.q)
    total = (await db.execute(count)).scalar_one()
    cond = order_by_fields(
        cond,
        query.sort_by,
        query.sort_order,
        {
            "value": BotCategory.value,
            "label": BotCategory.label,
            "sort_order": BotCategory.sort_order,
            "id": BotCategory.id,
        },
        BotCategory.sort_order,
    )
    rows = (await db.execute(cond.offset(pg.offset).limit(pg.page_size))).scalars().all()
    return ok({
        "total": total,
        "items": [_out(r) for r in rows],
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.get("/options")
async def bot_category_options(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(BotCategory).order_by(BotCategory.sort_order, BotCategory.id)
        )
    ).scalars().all()
    return ok([BotCategoryOption(value=r.value, label=r.label).model_dump() for r in rows])


@router.get("/{category_id}")
async def get_bot_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(BotCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bot 分类不存在")
    return ok(_out(row))


@router.post("")
async def create_bot_category(
    body: BotCategoryCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    existing = (
        await db.execute(select(BotCategory.id).where(BotCategory.value == body.value))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail=f"分类标识 {body.value!r} 已存在")
    row = BotCategory(
        value=body.value,
        label=body.label,
        sort_order=body.sort_order,
        remark=body.remark,
        is_builtin=False,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(_out(row))


@router.put("/{category_id}")
async def update_bot_category(
    category_id: int,
    body: BotCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(BotCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bot 分类不存在")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(_out(row))


@router.delete("/{category_id}")
async def delete_bot_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(BotCategory, category_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bot 分类不存在")
    if row.is_builtin or row.value == RESERVED_CATEGORY_OTHER:
        raise HTTPException(status_code=400, detail="系统内置分类不可删除")
    refs = await find_bot_category_references(db, row.value)
    if refs:
        raise HTTPException(
            status_code=400,
            detail=f"分类仍被引用，无法删除: {', '.join(refs)}",
        )
    await db.delete(row)
    await db.commit()
    await rule_sync.publish(db)
    return ok()
