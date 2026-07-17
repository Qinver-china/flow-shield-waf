"""Enrich log entries during ingest (UA parse, URI normalize)."""
from __future__ import annotations

import re

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I
)
_NUM_SEGMENT_RE = re.compile(r"/\d+")
_HEX_SEGMENT_RE = re.compile(r"/[0-9a-f]{16,}", re.I)


def normalize_uri_pattern(path: str | None) -> str:
    if not path:
        return "/"
    out = _UUID_RE.sub(":id", path)
    out = _NUM_SEGMENT_RE.sub("/:id", out)
    out = _HEX_SEGMENT_RE.sub("/:id", out)
    return out


def parse_ua(ua: str | None) -> tuple[str | None, str | None, str | None]:
    if not ua:
        return None, None, None
    ua_l = ua.lower()
    browser = None
    if "chrome" in ua_l and "edg" not in ua_l:
        browser = "Chrome"
    elif "firefox" in ua_l:
        browser = "Firefox"
    elif "safari" in ua_l and "chrome" not in ua_l:
        browser = "Safari"
    elif "edg" in ua_l:
        browser = "Edge"

    os_name = None
    if "windows" in ua_l:
        os_name = "Windows"
    elif "mac os" in ua_l or "macintosh" in ua_l:
        os_name = "macOS"
    elif "android" in ua_l:
        os_name = "Android"
    elif "iphone" in ua_l or "ipad" in ua_l:
        os_name = "iOS"
    elif "linux" in ua_l:
        os_name = "Linux"

    family = "bot" if "bot" in ua_l or "spider" in ua_l or "crawl" in ua_l else "browser"
    return family, os_name, browser


def _first_xff(headers: dict | None) -> str | None:
    if not isinstance(headers, dict):
        return None
    for key, value in headers.items():
        if str(key).lower() != "x-forwarded-for":
            continue
        if value is None:
            return None
        first = str(value).split(",", 1)[0].strip()
        return first or None
    return None


def enrich_entry(entry: dict) -> dict:
    out = dict(entry)
    path = out.get("uri_path") or out.get("uri") or "/"
    if isinstance(path, str) and "?" in path:
        path = path.split("?", 1)[0]
    out["uri_path"] = path
    out["uri_pattern"] = normalize_uri_pattern(path)
    ua = out.get("ua")
    family, os_name, browser = parse_ua(ua if isinstance(ua, str) else None)
    out["ua_family"] = family
    out["ua_os"] = os_name
    out["ua_browser"] = browser
    payload = out.get("payload")
    if isinstance(payload, dict):
        query = payload.get("query")
        if isinstance(query, dict):
            out["query_count"] = len(query)
        if not out.get("xff_first"):
            out["xff_first"] = _first_xff(payload.get("headers"))
    return out
