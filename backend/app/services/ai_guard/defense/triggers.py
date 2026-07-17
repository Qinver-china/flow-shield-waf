"""AI Guard trigger types and validation."""
from __future__ import annotations

from typing import Any

from app.models.ai_guard import APPLY_MODES

TRIGGER_TYPES: list[dict] = [
    {
        "type": "traffic.qps_gt",
        "label": "全局 QPS 超过阈值",
        "params": [
            {"key": "window_sec", "label": "时间窗口（秒）", "kind": "number", "required": True},
            {"key": "qps", "label": "QPS 阈值", "kind": "number", "required": True},
        ],
    },
    {
        "type": "traffic.abs_gt",
        "label": "窗口请求量超过阈值",
        "params": [
            {"key": "window_sec", "label": "时间窗口（秒）", "kind": "number", "required": True},
            {"key": "threshold", "label": "请求量阈值", "kind": "number", "required": True},
        ],
    },
    {
        "type": "security.block_rate",
        "label": "拦截率超过阈值",
        "params": [
            {"key": "window_min", "label": "统计窗口（分钟）", "kind": "number", "required": True},
            {"key": "percent", "label": "拦截率（%）", "kind": "number", "required": True},
            {"key": "site_id", "label": "生效站点", "kind": "site_id", "required": False},
        ],
    },
    {
        "type": "traffic_intel.anomaly",
        "label": "流量情报异常检测命中",
        "params": [
            {"key": "window_sec", "label": "时间窗口（秒）", "kind": "number", "required": False},
        ],
    },
]

TRIGGER_TYPE_MAP = {t["type"]: t for t in TRIGGER_TYPES}
NOTIFY_STAGES = ("trigger", "analyzing", "result")


def validate_apply_mode(mode: str) -> str:
    if mode not in APPLY_MODES:
        allowed = ", ".join(APPLY_MODES)
        raise ValueError(f"无效的应用模式 {mode}，可选: {allowed}")
    return mode


def validate_trigger_params(trigger_type: str, params: dict[str, Any] | None) -> dict:
    meta = TRIGGER_TYPE_MAP.get(trigger_type)
    if meta is None:
        raise ValueError(f"不支持的触发类型: {trigger_type}")
    params = dict(params or {})
    for spec in meta.get("params", []):
        key = spec["key"]
        label = spec.get("label") or key
        if spec.get("required") and params.get(key) in (None, ""):
            raise ValueError(f"触发参数「{label}」不能为空")
        if key in params and params[key] not in (None, ""):
            if spec.get("kind") in ("number",):
                params[key] = int(params[key])
            elif spec.get("kind") == "site_id":
                if params[key] in (None, ""):
                    params.pop(key, None)
                else:
                    params[key] = int(params[key])
    return params
