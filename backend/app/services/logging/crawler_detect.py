"""Crawler/bot detection via CrawlerDetect (JayBizzle, 3700+ patterns)."""
from __future__ import annotations

from crawlerdetect import CrawlerDetect

from app.services.bot_ua_heuristic import is_bot_ua_heuristic


def is_crawler_ua(ua: str | None) -> tuple[bool, str | None]:
    """Return (is_crawler, matched_name_or_none)."""
    if not ua or not ua.strip():
        return False, None
    detector = CrawlerDetect(user_agent=ua)
    if detector.isCrawler():
        match = detector.getMatches()
        name = match.strip() if isinstance(match, str) and match.strip() else None
        return True, name
    if is_bot_ua_heuristic(ua):
        return True, None
    return False, None
