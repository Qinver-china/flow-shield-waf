"""Scan enabled rule trees for fields that need request-body inspection."""

from __future__ import annotations

from typing import Any, Iterable

from app.constants.engine_settings import BODY_READ_FIELDS, UPLOAD_FIELDS


def collect_condition_fields(node: Any, out: set[str] | None = None) -> set[str]:
    """Collect `field` keys from a nested condition tree."""
    if out is None:
        out = set()
    if not isinstance(node, dict):
        return out
    field = node.get("field")
    if isinstance(field, str) and field:
        out.add(field)
    for child in node.get("conditions") or []:
        collect_condition_fields(child, out)
    return out


def inspect_flags_from_items(items: Iterable[dict]) -> dict[str, bool]:
    """Return whether any enabled item needs body or upload field extraction."""
    fields: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or item.get("enabled") is False:
            continue
        collect_condition_fields(item.get("conditions"), fields)
        for key in item.get("keys") or []:
            if not isinstance(key, dict):
                continue
            field = key.get("field")
            if isinstance(field, str) and field:
                fields.add(field)
    return {
        "body": bool(fields & BODY_READ_FIELDS),
        "upload": bool(fields & UPLOAD_FIELDS),
    }
