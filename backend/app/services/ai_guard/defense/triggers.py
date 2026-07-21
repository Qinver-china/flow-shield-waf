"""AI Guard trigger types and validation.

Aligned with alert policy conditions (see ``alert_conditions``), plus AI-only
``traffic_intel.anomaly``.
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
from app.services.notifications.validators import validate_condition_params

_AI_ONLY_TRIGGERS: list[dict] = [
    {
        "type": "traffic_intel.anomaly",
        "label": "流量情报异常检测命中",
        "category": "流量情报",
        "description": "当流量情报模块判定出现突增异常时触发（可限定窗口与站点）。",
        "params": [
            {
                "key": "window_sec",
                "label": "时间窗口",
                "kind": "traffic_window",
                "required": False,
                "help": "留空表示任意窗口命中均触发",
            },
            {
                "key": "site_id",
                "label": "生效站点",
                "kind": "site_id",
                "required": False,
                "help": "留空表示全站（含全局异常）",
            },
        ],
    },
]

TRIGGER_TYPES: list[dict] = [
    *[deepcopy(item) for item in ALERT_CONDITION_TYPES],
    *[deepcopy(item) for item in _AI_ONLY_TRIGGERS],
]

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
    if mode not in APPLY_MODES:
        allowed = ", ".join(APPLY_MODES)
        raise ValueError(f"无效的应用模式 {mode}，可选: {allowed}")
    return mode


def normalize_legacy_trigger_params(
    trigger_type: str,
    params: dict[str, Any] | None,
) -> dict[str, Any]:
    """Map legacy ``qps`` key to ``threshold`` for QPS triggers."""
    out = dict(params or {})
    if trigger_type in ("traffic.qps_gt", "traffic.qps_lt"):
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

    if trigger_type == "traffic_intel.anomaly":
        return _validate_ai_only_params(meta, params)

    return validate_condition_params(trigger_type, params)


def _validate_ai_only_params(meta: dict, params: dict[str, Any]) -> dict:
    """Validate params for AI-only trigger types not in the alert catalog."""
    from app.constants.traffic_windows import TRAFFIC_WINDOWS_SEC

    out = dict(params)
    for spec in meta.get("params", []):
        key = spec["key"]
        label = spec.get("label") or key
        if spec.get("required") and out.get(key) in (None, ""):
            raise ValueError(f"触发参数「{label}」不能为空")
        if key not in out or out[key] in (None, ""):
            if not spec.get("required"):
                out.pop(key, None)
            continue
        kind = spec.get("kind")
        if kind in ("number", "traffic_window", "block_window"):
            out[key] = int(out[key])
        elif kind == "site_id":
            out[key] = int(out[key])
        if kind == "traffic_window" and out[key] not in TRAFFIC_WINDOWS_SEC:
            raise ValueError("不支持的时间窗口")
    return out
