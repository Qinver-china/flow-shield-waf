"""Normalize multi-site scope (site_ids JSON) for API and storage."""
from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, text
from sqlalchemy.orm.attributes import InstrumentedAttribute


def resolved_site_ids(row: Any) -> list[int]:
    raw = getattr(row, "site_ids", None)
    if raw:
        return [int(x) for x in raw]
    return []


def apply_site_scope(data: dict[str, Any]) -> dict[str, Any]:
    if "site_ids" not in data:
        return data
    ids = data.get("site_ids")
    if ids is None:
        return data
    ids = [int(i) for i in ids if i is not None]
    data["site_ids"] = ids if ids else None
    return data


def enrich_row(row: Any, payload: dict[str, Any]) -> dict[str, Any]:
    payload["site_ids"] = resolved_site_ids(row)
    return payload


def site_scope_filter(
    site_ids_col: InstrumentedAttribute[list | None],
    target_site_id: int,
) -> ColumnElement[bool]:
    """Match rows explicitly bound to target_site_id (global/unscoped rows excluded)."""
    _ = site_ids_col  # column identity for callers; SQL uses physical column name
    return text(
        "EXISTS (SELECT 1 FROM json_each(COALESCE(NULLIF(site_ids, 'null'), '[]')) AS je "
        "WHERE CAST(je.value AS INTEGER) = :sid)"
    ).bindparams(sid=target_site_id)
