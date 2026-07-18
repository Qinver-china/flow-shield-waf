"""Shared reference integrity checks for scoped resources."""
from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BotProfile, IpGroup, Site


async def ensure_site_ids_exist(db: AsyncSession, site_ids: list[int] | None) -> None:
    if not site_ids:
        return
    rows = (
        await db.execute(select(Site.id).where(Site.id.in_(site_ids)))
    ).scalars().all()
    missing = sorted(set(site_ids) - set(rows))
    if missing:
        raise HTTPException(status_code=400, detail=f"站点不存在: {missing}")


async def ensure_ip_group_ids_exist(db: AsyncSession, group_ids: list[int]) -> None:
    if not group_ids:
        return
    rows = (
        await db.execute(select(IpGroup.id).where(IpGroup.id.in_(group_ids)))
    ).scalars().all()
    missing = sorted(set(group_ids) - set(rows))
    if missing:
        raise HTTPException(status_code=400, detail=f"IP 组不存在: {missing}")


def _collect_ip_group_ids(node: Any, out: set[int]) -> None:
    if not isinstance(node, dict):
        return
    if "conditions" in node:
        for child in node.get("conditions") or []:
            _collect_ip_group_ids(child, out)
        return
    op = node.get("op")
    if op in {"in_ip_group", "not_in_ip_group"}:
        value = node.get("value") or []
        if isinstance(value, list):
            for item in value:
                if isinstance(item, int) and item > 0:
                    out.add(item)


async def validate_condition_references(
    db: AsyncSession,
    condition: dict | None,
) -> None:
    if not condition:
        return
    group_ids: set[int] = set()
    _collect_ip_group_ids(condition, group_ids)
    await ensure_ip_group_ids_exist(db, sorted(group_ids))


def _iter_condition_nodes(raw: Any):
    if raw is None:
        return
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return
    if isinstance(raw, dict):
        yield raw
        for child in raw.get("conditions") or []:
            yield from _iter_condition_nodes(child)


async def find_ip_group_references(db: AsyncSession, group_id: int) -> list[str]:
    from app.models import Exception_, IpList, RateLimit, Rule

    refs: list[str] = []
    models = [
        ("规则", Rule),
        ("黑白名单", IpList),
        ("防护例外", Exception_),
        ("速率防护", RateLimit),
    ]
    for label, model in models:
        rows = (await db.execute(select(model))).scalars().all()
        for row in rows:
            for node in _iter_condition_nodes(getattr(row, "conditions", None)):
                op = node.get("op")
                if op not in {"in_ip_group", "not_in_ip_group"}:
                    continue
                value = node.get("value") or []
                if group_id in value:
                    refs.append(f"{label} #{row.id} {getattr(row, 'name', '')}".strip())
                    break
    return refs


def _collect_bot_category_values(node: Any, out: set[str]) -> None:
    if not isinstance(node, dict):
        return
    if "conditions" in node:
        for child in node.get("conditions") or []:
            _collect_bot_category_values(child, out)
        return
    if node.get("field") != "bot.category":
        return
    op = node.get("op")
    value = node.get("value")
    if op in {"eq", "equals"} and isinstance(value, str) and value:
        out.add(value)
    elif op in {"in_list", "not_in"} and isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item:
                out.add(item)


async def find_bot_category_references(db: AsyncSession, category_value: str) -> list[str]:
    from app.models import Exception_, IpList, RateLimit, Rule

    refs: list[str] = []
    count = (
        await db.execute(
            select(func.count(BotProfile.id)).where(BotProfile.category == category_value)
        )
    ).scalar_one()
    if count:
        refs.append(f"Bot 库 ({count} 条)")

    models = [
        ("规则", Rule),
        ("黑白名单", IpList),
        ("防护例外", Exception_),
        ("速率防护", RateLimit),
    ]
    for label, model in models:
        rows = (await db.execute(select(model))).scalars().all()
        for row in rows:
            values: set[str] = set()
            for node in _iter_condition_nodes(getattr(row, "conditions", None)):
                _collect_bot_category_values(node, values)
            if category_value in values:
                refs.append(f"{label} #{row.id} {getattr(row, 'name', '')}".strip())
    return refs
