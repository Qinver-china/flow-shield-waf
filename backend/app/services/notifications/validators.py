"""Validate alert policy condition parameters."""
from __future__ import annotations

from typing import Any

from app.constants.alert_conditions import CONDITION_TYPE_MAP
from app.constants.traffic_windows import TRAFFIC_BASELINE_MIN_WINDOW_SEC, TRAFFIC_WINDOWS_SEC


_BASELINE_CONDITIONS = frozenset({"traffic.baseline_gt", "traffic.baseline_lt"})
_QPS_CONDITIONS = frozenset({"traffic.qps_gt", "traffic.qps_lt"})


def validate_condition_params(condition_type: str, params: dict[str, Any] | None) -> dict:
    meta = CONDITION_TYPE_MAP.get(condition_type)
    if meta is None:
        raise ValueError(f"不支持的预警条件: {condition_type}")
    params = dict(params or {})
    if not meta.get("params"):
        return {}
    for spec in meta["params"]:
        key = spec["key"]
        required = spec.get("required", True)
        if required and params.get(key) in (None, ""):
            raise ValueError(f"条件参数「{spec['label']}」不能为空")
        if key in params and params[key] not in (None, ""):
            if spec.get("kind") in ("number", "traffic_window", "block_window"):
                try:
                    params[key] = int(params[key])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"参数「{spec['label']}」必须是数字") from exc
            if spec.get("kind") == "site_id":
                if params[key] in (None, ""):
                    params.pop(key, None)
                else:
                    params[key] = int(params[key])
        elif spec.get("kind") == "site_id" and not required:
            params.pop(key, None)
    if condition_type in _BASELINE_CONDITIONS:
        window_sec = params.get("window_sec")
        if window_sec is not None and int(window_sec) < TRAFFIC_BASELINE_MIN_WINDOW_SEC:
            raise ValueError("基线比较不支持短于 5 分钟的窗口，请选择 5 分钟或 30 分钟")
    if condition_type.startswith("traffic."):
        window_sec = params.get("window_sec")
        if window_sec is not None and int(window_sec) not in TRAFFIC_WINDOWS_SEC:
            raise ValueError("不支持的时间窗口")
    if condition_type in _QPS_CONDITIONS:
        threshold = params.get("threshold")
        if threshold is not None and float(threshold) < 0:
            raise ValueError("QPS 阈值不能为负数")
    return params
