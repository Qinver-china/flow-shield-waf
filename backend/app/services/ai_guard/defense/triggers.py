"""AI Guard trigger types and validation.

Aligned with alert policy conditions (see ``alert_conditions``).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.constants.alert_conditions import (
    ALERT_CONDITION_TYPES,
    BLOCK_WINDOWS_MIN,
    SYSTEM_WINDOWS,
    TRAFFIC_WINDOWS,
)
from app.models.ai_guard import APPLY_MODES
from app.services.ai_guard.mode_guide import normalize_apply_mode
from app.services.notifications.validators import validate_condition_params

TRIGGER_TYPES: list[dict] = [deepcopy(item) for item in ALERT_CONDITION_TYPES]

TRIGGER_TYPE_MAP = {t["type"]: t for t in TRIGGER_TYPES}
NOTIFY_STAGES = ("trigger", "analyzing", "result")

# Re-export window catalogs for the meta API / UI selects.
__all__ = (
    "BLOCK_WINDOWS_MIN",
    "NOTIFY_STAGES",
    "SYSTEM_WINDOWS",
    "TRAFFIC_WINDOWS",
    "TRIGGER_TYPES",
    "TRIGGER_TYPE_MAP",
    "normalize_legacy_trigger_params",
    "validate_apply_mode",
    "validate_trigger_params",
)


def validate_apply_mode(mode: str) -> str:
    normalized = normalize_apply_mode(mode, default="")
    if normalized not in APPLY_MODES:
        allowed = ", ".join(APPLY_MODES)
        raise ValueError(f"无效的应用模式 {mode}，可选: {allowed}")
    return normalized


def normalize_legacy_trigger_params(
    trigger_type: str,
    params: dict[str, Any] | None,
) -> dict[str, Any]:
    """Map legacy ``qps`` key to ``threshold`` for QPS triggers."""
    out = dict(params or {})
    if trigger_type in ("traffic.qps_gt", "traffic.qps_lt", "traffic.origin_qps_gt", "traffic.origin_qps_lt"):
        if out.get("threshold") in (None, "") and out.get("qps") not in (None, ""):
            out["threshold"] = out.pop("qps")
        else:
            out.pop("qps", None)
    return out


def validate_trigger_params(trigger_type: str, params: dict[str, Any] | None) -> dict:
    """Validate and coerce trigger params for an AI Guard policy."""
    meta = TRIGGER_TYPE_MAP.get(trigger_type)
    if meta is None:
        raise ValueError(f"不支持的触发类型: {trigger_type}")

    params = normalize_legacy_trigger_params(trigger_type, params)
    return validate_condition_params(trigger_type, params)
