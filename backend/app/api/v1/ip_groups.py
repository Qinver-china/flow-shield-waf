from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.api.deps import Pagination, get_current_user
from app.api.listing import ListQuery, get_list_query, order_by_fields
from app.core.db import get_db
from app.models import IpGroup, User
from app.schemas.common import ok
from app.schemas.ip_group import (
    IpGroupBatchEntries,
    IpGroupCreate,
    IpGroupOption,
    IpGroupOut,
    IpGroupUpdate,
)
from app.services import rule_sync
from app.services.reference_validation import find_ip_group_references
from app.services.ip_entry import normalize_entries, parse_lines

router = APIRouter()


def _out(row: IpGroup) -> dict:
    data = IpGroupOut.model_validate(row).model_dump()
    data["entry_count"] = len(row.entries or [])
    return data


def _apply_ip_group_q(stmt: Select, q: str | None) -> Select:
    if not q:
        return stmt
    pattern = f"%{q}%"
    entries_text = cast(IpGroup.entries, String)
    return stmt.where(
        or_(
            IpGroup.name.like(pattern),
            IpGroup.remark.like(pattern),
            entries_text.like(pattern),
        )
    )


def _normalize_body_entries(body: IpGroupBatchEntries) -> list[str]:
    raw: list[str] = []
    if body.entries:
        raw.extend(body.entries)
    if body.text:
        raw.extend(parse_lines(body.text))
    if not raw:
        raise HTTPException(status_code=400, detail="请提供 IP 条目")
    try:
        return normalize_entries(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
async def list_ip_groups(
    pg: Pagination = Depends(),
    query: ListQuery = Depends(get_list_query),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cond = select(IpGroup)
    count = select(func.count(IpGroup.id))
    cond = _apply_ip_group_q(cond, query.q)
    count = _apply_ip_group_q(count, query.q)
    total = (await db.execute(count)).scalar_one()
    cond = order_by_fields(
        cond,
        query.sort_by,
        query.sort_order,
        {"name": IpGroup.name, "id": IpGroup.id},
        IpGroup.id,
    )
    rows = (await db.execute(cond.offset(pg.offset).limit(pg.page_size))).scalars().all()
    return ok({
        "total": total,
        "items": [_out(r) for r in rows],
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.get("/options")
async def ip_group_options(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = (await db.execute(select(IpGroup).order_by(IpGroup.name.asc()))).scalars().all()
    return ok([
        IpGroupOption(
            id=r.id,
            name=r.name,
            entry_count=len(r.entries or []),
        ).model_dump()
        for r in rows
    ])


@router.get("/{group_id}")
async def get_ip_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(IpGroup, group_id)
    if row is None:
        raise HTTPException(status_code=404, detail="IP 组不存在")
    return ok(_out(row))


@router.post("")
async def create_ip_group(
    body: IpGroupCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="请填写名称")
    try:
        entries = normalize_entries(body.entries or [])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = IpGroup(name=name, remark=body.remark, entries=entries)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(_out(row))


@router.put("/{group_id}")
async def update_ip_group(
    group_id: int,
    body: IpGroupUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(IpGroup, group_id)
    if row is None:
        raise HTTPException(status_code=404, detail="IP 组不存在")
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="请填写名称")
        row.name = name
    if "remark" in data:
        row.remark = data["remark"]
    if "entries" in data:
        try:
            row.entries = normalize_entries(data["entries"] or [])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(_out(row))


@router.post("/{group_id}/entries/batch")
async def batch_add_entries(
    group_id: int,
    body: IpGroupBatchEntries,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(IpGroup, group_id)
    if row is None:
        raise HTTPException(status_code=404, detail="IP 组不存在")
    new_entries = _normalize_body_entries(body)
    merged = normalize_entries([*(row.entries or []), *new_entries])
    row.entries = merged
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(_out(row))


@router.post("/{group_id}/entries/import")
async def import_entries(
    group_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(IpGroup, group_id)
    if row is None:
        raise HTTPException(status_code=404, detail="IP 组不存在")
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="文件需为 UTF-8 编码文本") from exc
    body = IpGroupBatchEntries(text=text)
    new_entries = _normalize_body_entries(body)
    merged = normalize_entries([*(row.entries or []), *new_entries])
    row.entries = merged
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(_out(row))


@router.delete("/{group_id}")
async def delete_ip_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(IpGroup, group_id)
    if row is None:
        raise HTTPException(status_code=404, detail="IP 组不存在")
    refs = await find_ip_group_references(db, group_id)
    if refs:
        raise HTTPException(
            status_code=400,
            detail=f"IP 组仍被引用，无法删除: {', '.join(refs[:5])}",
        )
    await db.delete(row)
    await db.commit()
    await rule_sync.publish(db)
    return ok()
