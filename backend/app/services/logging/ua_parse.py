"""User-Agent parsing for log enrichment (ua-parser + CrawlerDetect)."""
from __future__ import annotations

from ua_parser import parse_os, parse_user_agent

from app.services.logging.crawler_detect import is_crawler_ua

# Normalize ua-parser families to stable dashboard labels.
_OS_LABELS: dict[str, str] = {
    "Mac OS X": "macOS",
    "Mac OS": "macOS",
    "Windows": "Windows",
    "Android": "Android",
    "iOS": "iOS",
    "Linux": "Linux",
    "Chrome OS": "Chrome OS",
    "Ubuntu": "Linux",
    "Debian": "Linux",
    "Fedora": "Linux",
}

_BROWSER_LABELS: dict[str, str] = {
    "Chrome Mobile": "Chrome",
    "Chrome Mobile iOS": "Chrome",
    "Mobile Safari": "Safari",
    "Chrome": "Chrome",
    "Firefox": "Firefox",
    "Safari": "Safari",
    "Edge": "Edge",
    "Opera": "Opera",
    "IE": "IE",
    "Samsung Internet": "Samsung Internet",
}


def _normalize_os(family: str | None) -> str | None:
    if not family or family == "Other":
        return None
    return _OS_LABELS.get(family, family)


def _normalize_browser(family: str | None) -> str | None:
    if not family or family == "Other":
        return None
    return _BROWSER_LABELS.get(family, family)


def parse_client_ua(ua: str | None) -> tuple[str | None, str | None, str | None]:
    """Return (ua_family, ua_os, ua_browser)."""
    if not ua or not ua.strip():
        return None, None, None

    browser_parsed = parse_user_agent(ua)
    os_parsed = parse_os(ua)
    os_name = _normalize_os(os_parsed.family if os_parsed else None)
    browser = _normalize_browser(browser_parsed.family if browser_parsed else None)

    is_crawler, _ = is_crawler_ua(ua)
    if is_crawler:
        return "bot", os_name, None

    return "browser", os_name, browser
