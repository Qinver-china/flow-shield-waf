"""Vendored crawler UA matching (fallback when engine did not enrich logs)."""
from __future__ import annotations

from functools import lru_cache

from app.services.bot_ua_heuristic import is_bot_ua_heuristic
from app.services.crawler_vendored.compile import match_crawler_name
from app.services.crawler_vendored.store import load_compiled_config


@lru_cache(maxsize=1)
def _compiled() -> tuple[str, str]:
    cfg = load_compiled_config()
    return cfg.get("patterns", ""), cfg.get("exclusions", "")


def invalidate_match_cache() -> None:
    _compiled.cache_clear()


def is_crawler_ua(ua: str | None) -> tuple[bool, str | None]:
    if not ua or not ua.strip():
        return False, None
    patterns, exclusions = _compiled()
    if patterns:
        name = match_crawler_name(ua, patterns=patterns, exclusions=exclusions)
        if name:
            return True, name
    if is_bot_ua_heuristic(ua):
        return True, None
    return False, None
