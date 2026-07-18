"""Shared list query helpers for paginated admin tables."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Query
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql import Select

from app.services.site_scope import site_scope_filter


@dataclass
class ListQuery:
    q: str | None
    sort_by: str | None
    sort_order: str
    enabled: bool | None
    site_id: list[int] | None
    mode: str | None
    scope: str | None
    expiry: str | None


def get_list_query(
    q: str | None = Query(None, description="搜索关键词"),
    sort_by: str | None = Query(None, description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    enabled: bool | None = Query(None, description="启用状态"),
    site_id: list[int] | None = Query(None, description="生效站点，可多选"),
    mode: str | None = Query(None, description="防护模式"),
    scope: str | None = Query(None, description="例外范围"),
    expiry: str | None = Query(
        None,
        pattern="^(expired|soon|valid)$",
        description="证书到期筛选",
    ),
) -> ListQuery:
    keyword = q.strip() if q and q.strip() else None
    return ListQuery(
        q=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
        enabled=enabled,
        site_id=site_id,
        mode=mode,
        scope=scope,
        expiry=expiry,
    )


def apply_q_filter(
    stmt: Select,
    q: str | None,
    *columns: InstrumentedAttribute,
) -> Select:
    if not q or not columns:
        return stmt
    pattern = f"%{q}%"
    return stmt.where(or_(*[col.like(pattern) for col in columns]))


def apply_enabled_filter(
    stmt: Select,
    column: InstrumentedAttribute,
    enabled: bool | None,
) -> Select:
    if enabled is None:
        return stmt
    return stmt.where(column == enabled)


def apply_mode_filter(
    stmt: Select,
    column: InstrumentedAttribute,
    mode: str | None,
) -> Select:
    if not mode:
        return stmt
    return stmt.where(column == mode)


def apply_scope_filter(
    stmt: Select,
    column: InstrumentedAttribute,
    scope: str | None,
) -> Select:
    if not scope:
        return stmt
    return stmt.where(column == scope)


def apply_site_filter(
    stmt: Select,
    site_ids_col: InstrumentedAttribute,
    site_id: int | list[int] | None,
) -> Select:
    if site_id is None:
        return stmt
    site_ids = [site_id] if isinstance(site_id, int) else [int(x) for x in site_id]
    site_ids = [sid for sid in site_ids if sid is not None]
    if not site_ids:
        return stmt
    if len(site_ids) == 1:
        return stmt.where(site_scope_filter(site_ids_col, site_ids[0]))
    return stmt.where(
        or_(*[site_scope_filter(site_ids_col, sid) for sid in site_ids])
    )


def apply_cert_expiry_filter(
    stmt: Select,
    not_after_col: InstrumentedAttribute,
    expiry: str | None,
) -> Select:
    if not expiry:
        return stmt
    now = datetime.utcnow()
    soon = now + timedelta(days=30)
    if expiry == "expired":
        return stmt.where(not_after_col.is_not(None), not_after_col < now)
    if expiry == "soon":
        return stmt.where(
            not_after_col.is_not(None),
            not_after_col >= now,
            not_after_col < soon,
        )
    if expiry == "valid":
        return stmt.where(or_(not_after_col.is_(None), not_after_col >= now))
    return stmt


def order_by_fields(
    stmt: Select,
    sort_by: str | None,
    sort_order: str,
    allowed: dict[str, InstrumentedAttribute],
    *default: InstrumentedAttribute,
    tiebreaker: InstrumentedAttribute | None = None,
) -> Select:
    ordering = []
    if sort_by and sort_by in allowed:
        column = allowed[sort_by]
        ordering.append(desc(column) if sort_order == "desc" else asc(column))
        if tiebreaker is not None:
            ordering.append(desc(tiebreaker))
    else:
        for column in default:
            ordering.append(desc(column))
    return stmt.order_by(*ordering)
