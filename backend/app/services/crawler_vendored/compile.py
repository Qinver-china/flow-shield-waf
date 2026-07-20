"""Compile JayBizzle Crawler-Detect JSON fixtures into engine regex bundles."""
from __future__ import annotations

import re


def compile_alternation(patterns: list[str]) -> str:
    if not patterns:
        return ""
    return f"({'|'.join(patterns)})"


def compile_bundle(crawlers: list[str], exclusions: list[str]) -> dict[str, str]:
    return {
        "patterns": compile_alternation(crawlers),
        "exclusions": compile_alternation(exclusions),
    }


def match_crawler_name(ua: str, *, patterns: str, exclusions: str) -> str | None:
    """Mirror engine/lua/waf/bot.lua + legacy crawlerdetect Python semantics."""
    if not ua or not ua.strip():
        return None
    agent = ua
    if exclusions:
        agent = re.sub(exclusions, "", agent, flags=re.IGNORECASE)
    if not agent:
        return None
    if not patterns:
        return None
    match = re.search(patterns, agent, flags=re.IGNORECASE)
    if not match:
        return None
    if match.lastindex:
        for idx in range(1, match.lastindex + 1):
            group = match.group(idx)
            if group:
                return group.strip()
    full = match.group(0)
    return full.strip() if full else None
