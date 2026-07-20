"""Enrich log entries during ingest (UA parse, URI normalize, bot dimensions)."""
from __future__ import annotations

import re
from typing import Any

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


def _engine_enriched_bot(entry: dict) -> bool:
    return entry.get("bot_name") is not None or entry.get("bot_category") is not None


def _enrich_one(
    entry: dict,
    *,
    bots: list[dict[str, Any]],
    categories: set[str] | None,
) -> dict:
    out = dict(entry)
    raw_uri = out.get("request_uri") or out.get("uri")
    path = out.get("uri_path")
    if not path:
        path = raw_uri or "/"
    if isinstance(path, str) and "?" in path:
        path = path.split("?", 1)[0]
    out["uri_path"] = path
    if raw_uri:
        out["request_uri"] = raw_uri
    out.pop("uri", None)
    out["uri_pattern"] = normalize_uri_pattern(path)

    ua = out.get("ua")
    ua_str = ua if isinstance(ua, str) else None

    if _engine_enriched_bot(out):
        out["ua_family"] = "bot"
        out["ua_browser"] = None
    else:
        if out.get("ua_family") is None:
            family, os_name, browser = parse_client_ua(ua_str)
            out["ua_family"] = family
            if out.get("ua_os") is None:
                out["ua_os"] = os_name
            if out.get("ua_browser") is None:
                out["ua_browser"] = browser
        elif out.get("ua_family") == "bot":
            out["ua_browser"] = None
            if out.get("ua_os") is None and ua_str:
                _, os_name, _ = parse_client_ua(ua_str)
                out["ua_os"] = os_name
        elif ua_str and out.get("ua_browser") is None:
            _, os_name, browser = parse_client_ua(ua_str)
            if out.get("ua_os") is None:
                out["ua_os"] = os_name
            out["ua_browser"] = browser

        if out.get("bot_name") is None and out.get("bot_category") is None:
            bot_name, bot_category = resolve_bot_dimensions(
                ua_str,
                _site_id_value(out),
                bots,
                categories,
            )
            if bot_name or bot_category:
                out["bot_name"] = bot_name
                out["bot_category"] = bot_category
                out["ua_family"] = "bot"
                out["ua_browser"] = None
        elif out.get("bot_name") or out.get("bot_category"):
            out["ua_family"] = "bot"
            out["ua_browser"] = None

    if not out.get("bot_name") and not out.get("bot_category"):
        out["bot_name"] = None
        out["bot_category"] = None

    payload = out.get("payload")
    if isinstance(payload, dict):
        if out.get("query_count") is None:
            query = payload.get("query")
            if isinstance(query, dict):
                out["query_count"] = len(query)
        if not out.get("xff_first"):
            out["xff_first"] = _first_xff(payload.get("headers"))
    return out


def enrich_entry(entry: dict) -> dict:
    return _enrich_one(
        entry,
        bots=get_bots(),
        categories=get_category_values() or None,
    )


def enrich_entries(entries: list[dict]) -> list[dict]:
    """Enrich a batch sharing one bot-catalog snapshot (same result as enrich_entry)."""
    if not entries:
        return []
    bots = get_bots()
    categories = get_category_values() or None
    return [_enrich_one(entry, bots=bots, categories=categories) for entry in entries]
