"""Bot UA pattern validation and category helpers."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.bot_settings import (
    RESERVED_CATEGORY_OTHER,
    RESERVED_CATEGORY_VALUES,
)
from app.models import BotCategory

_REGEX_WRAPPED = re.compile(r"^/(.*)/([a-z]*)$", re.I)
_CATEGORY_VALUE_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")


def normalize_patterns(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        pat = item.strip()
        if not pat or pat in seen:
            continue
        validate_pattern(pat)
        seen.add(pat)
        out.append(pat)
    return out


def validate_pattern(pattern: str) -> None:
    if not pattern:
        raise ValueError("UA 匹配模式不能为空")
    wrapped = _REGEX_WRAPPED.match(pattern)
    if wrapped:
        body, flags = wrapped.group(1), wrapped.group(2) or ""
        try:
            re.compile(body, flags)
        except re.error as exc:
            raise ValueError(f"无效的正则模式: {pattern}") from exc
        return
    if len(pattern) > 512:
        raise ValueError("UA 匹配模式过长（最多 512 字符）")


def validate_category_value(value: str) -> str:
    slug = value.strip().lower()
    if not _CATEGORY_VALUE_RE.match(slug):
        raise ValueError("分类标识须为小写字母/数字/下划线，2–32 字符，且以字母开头")
    if slug in RESERVED_CATEGORY_VALUES:
        raise ValueError(f"分类标识 {slug!r} 为系统预留，不可新建")
    return slug


def normalize_category_slug(
    slug: str | None,
    known_values: set[str] | frozenset[str] | None = None,
) -> str:
    """Map invalid or missing category slugs to the reserved default."""
    if not slug:
        return RESERVED_CATEGORY_OTHER
    if known_values and slug not in known_values:
        return RESERVED_CATEGORY_OTHER
    return slug


async def list_category_values(db: AsyncSession) -> list[str]:
    rows = (
        await db.execute(select(BotCategory.value).order_by(BotCategory.sort_order, BotCategory.id))
    ).scalars().all()
    return list(rows)


async def ensure_category_exists(db: AsyncSession, category: str) -> str:
    slug = category.strip()
    if not slug:
        raise ValueError("请选择 Bot 分类")
    row = (
        await db.execute(select(BotCategory.value).where(BotCategory.value == slug))
    ).scalar_one_or_none()
    if row is None:
        raise ValueError(f"无效的 Bot 分类: {slug}")
    return slug


async def category_options(db: AsyncSession) -> list[dict[str, str]]:
    rows = (
        await db.execute(
            select(BotCategory).order_by(BotCategory.sort_order, BotCategory.id)
        )
    ).scalars().all()
    return [{"value": row.value, "label": row.label} for row in rows]


async def category_label_map(db: AsyncSession) -> dict[str, str]:
    rows = (await db.execute(select(BotCategory))).scalars().all()
    return {row.value: row.label for row in rows}
