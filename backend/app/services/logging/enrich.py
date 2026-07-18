"""Enrich log entries during ingest (UA parse, URI normalize, bot dimensions)."""
from __future__ import annotations

import re

from app.services.bot_identify import resolve_bot_dimensions
from app.services.logging.bot_catalog_snapshot import get_bots, get_category_values
from app.services.logging.ua_parse import parse_client_ua

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
    """Backward-compatible alias used by tests and callers."""
    return parse_client_ua(ua)


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


def _site_id_value(entry: dict) -> int | None:
    raw = entry.get("site_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def enrich_entry(entry: dict) -> dict:
    out = dict(entry)
    path = out.get("uri_path") or out.get("uri") or "/"
    if isinstance(path, str) and "?" in path:
        path = path.split("?", 1)[0]
    out["uri_path"] = path
    out["uri_pattern"] = normalize_uri_pattern(path)

    ua = out.get("ua")
    ua_str = ua if isinstance(ua, str) else None
    family, os_name, browser = parse_client_ua(ua_str)
    out["ua_family"] = family
    out["ua_os"] = os_name
    out["ua_browser"] = browser

    bot_name, bot_category = resolve_bot_dimensions(
        ua_str,
        _site_id_value(out),
        get_bots(),
        get_category_values() or None,
    )
    if bot_name or bot_category:
        out["bot_name"] = bot_name
        out["bot_category"] = bot_category
        out["ua_family"] = "bot"
        out["ua_browser"] = None
    else:
        out["bot_name"] = None
        out["bot_category"] = None

    payload = out.get("payload")
    if isinstance(payload, dict):
        query = payload.get("query")
        if isinstance(query, dict):
            out["query_count"] = len(query)
        if not out.get("xff_first"):
            out["xff_first"] = _first_xff(payload.get("headers"))
    return out
