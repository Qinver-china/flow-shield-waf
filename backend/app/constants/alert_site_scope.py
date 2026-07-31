"""Site scope for alert / AI Guard trigger conditions."""
from __future__ import annotations

from typing import Any

SITE_SCOPE_ALL = "all"
SITE_SCOPE_ANY = "any"
SITE_SCOPE_SINGLE = "single"

SITE_SCOPE_OPTIONS = [
    {"value": SITE_SCOPE_ALL, "label": "全部站点（合计）"},
    {"value": SITE_SCOPE_ANY, "label": "任意站点（任一满足）"},
]


def normalize_site_scope_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize legacy params (site_id only) into explicit site_scope."""
    out = dict(params or {})
    scope = out.get("site_scope")
    site_id = out.get("site_id")

    if scope in (None, ""):
        if site_id not in (None, ""):
            out["site_scope"] = SITE_SCOPE_SINGLE
        else:
            out["site_scope"] = SITE_SCOPE_ALL
            out.pop("site_id", None)
        return out

    scope = str(scope)
    if scope == SITE_SCOPE_ALL:
        out["site_scope"] = SITE_SCOPE_ALL
        out.pop("site_id", None)
        return out
    if scope == SITE_SCOPE_ANY:
        out["site_scope"] = SITE_SCOPE_ANY
        out.pop("site_id", None)
        return out
    if scope == SITE_SCOPE_SINGLE:
        out["site_scope"] = SITE_SCOPE_SINGLE
        if site_id in (None, ""):
            raise ValueError("选择「指定站点」时必须选择站点")
        out["site_id"] = int(site_id)
        return out
    raise ValueError(f"不支持的生效站点范围: {scope}")


def parse_site_scope(params: dict[str, Any] | None) -> tuple[str, int | None]:
    """Return (site_scope, site_id). site_id is set only for single scope."""
    normalized = normalize_site_scope_params(params)
    scope = normalized["site_scope"]
    site_id = normalized.get("site_id")
    if scope == SITE_SCOPE_SINGLE:
        return scope, int(site_id)
    return scope, None


def site_scope_label(scope: str, site_id: int | None = None) -> str:
    if scope == SITE_SCOPE_ANY:
        return "任意站点"
    if scope == SITE_SCOPE_SINGLE and site_id is not None:
        return f"站点 #{site_id}"
    return "全站"
