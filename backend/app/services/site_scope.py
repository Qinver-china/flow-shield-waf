"""Normalize multi-site scope (site_ids JSON) for API and storage."""
from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, or_, text
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
    """Match global rules (NULL/empty site_ids) or rows scoped to target_site_id."""
    return or_(
        site_ids_col.is_(None),
        text("JSON_LENGTH(COALESCE(site_ids, JSON_ARRAY())) = 0"),
        text("JSON_CONTAINS(site_ids, CAST(:sid AS JSON), '$')").bindparams(
            sid=target_site_id
        ),
    )
