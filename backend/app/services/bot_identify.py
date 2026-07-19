"""Bot identification from UA patterns (aligned with engine/lua/waf/bot.lua)."""
from __future__ import annotations

import re
from typing import Any

from app.constants.bot_settings import RESERVED_CATEGORY_OTHER
from app.services.bot_ua_heuristic import is_bot_ua_heuristic
from app.services.logging.crawler_detect import is_crawler_ua

_REGEX_WRAPPED = re.compile(r"^/(.*)/([a-z]*)$", re.I)


def match_ua_pattern(ua: str, pattern: str) -> bool:
    if not ua or not pattern:
        return False
    wrapped = _REGEX_WRAPPED.match(pattern.strip())
    if wrapped:
        body, flags = wrapped.group(1), wrapped.group(2) or ""
        try:
            return re.search(body, ua, flags) is not None
        except re.error:
            return False
    return pattern.lower() in ua.lower()


def _applies_site(item: dict[str, Any], site_id: int | None) -> bool:
    site_ids = item.get("site_ids")
    if not site_ids:
        return True
    if not isinstance(site_ids, list) or len(site_ids) == 0:
        return True
    if site_id is None:
        return False
    return any(int(sid) == int(site_id) for sid in site_ids)


def identify_bot(
    ua: str | None,
    site_id: int | None,
    bots: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Return {name, category} when UA matches an enabled bot profile."""
    if not ua or not bots:
        return None
    for item in bots:
        if item.get("enabled") is False:
            continue
        if not _applies_site(item, site_id):
            continue
        patterns = item.get("ua_patterns") or []
        for pattern in patterns:
            if isinstance(pattern, str) and match_ua_pattern(ua, pattern):
                return {
                    "name": item.get("name"),
                    "category": item.get("category"),
                }
    return None


def normalize_category_slug(
    slug: str | None,
    known_values: set[str] | frozenset[str] | None = None,
) -> str:
    if not slug:
        return RESERVED_CATEGORY_OTHER
    if known_values and slug not in known_values:
        return RESERVED_CATEGORY_OTHER
    return slug


def resolve_bot_dimensions(
    ua: str | None,
    site_id: int | None,
    bots: list[dict[str, Any]] | None,
    known_categories: set[str] | frozenset[str] | None = None,
) -> tuple[str | None, str | None]:
    """Return (bot_name, bot_category) for log enrichment."""
    bot_match = identify_bot(ua, site_id, bots)
    if bot_match:
        name = bot_match.get("name")
        category = normalize_category_slug(bot_match.get("category"), known_categories)
        return name, category

    is_crawler, crawler_name = is_crawler_ua(ua)
    if is_crawler or is_bot_ua_heuristic(ua):
        return crawler_name or None, RESERVED_CATEGORY_OTHER

    return None, None
