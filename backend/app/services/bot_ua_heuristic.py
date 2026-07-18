"""Lightweight UA keyword heuristics shared by bot identification paths."""
from __future__ import annotations

_BOT_UA_KEYWORDS = ("bot", "spider", "crawl")


def is_bot_ua_heuristic(ua: str | None) -> bool:
    if not ua:
        return False
    ua_l = ua.lower()
    return any(kw in ua_l for kw in _BOT_UA_KEYWORDS)
