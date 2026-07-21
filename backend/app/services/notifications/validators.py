"""Validate alert policy condition parameters."""
from __future__ import annotations

from typing import Any

from app.constants.alert_conditions import CONDITION_TYPE_MAP
from app.constants.system_metrics import SYSTEM_METRIC_WINDOWS_SEC
from app.constants.traffic_windows import TRAFFIC_BASELINE_MIN_WINDOW_SEC, TRAFFIC_WINDOWS_SEC


_BASELINE_CONDITIONS = frozenset({"traffic.baseline_gt", "traffic.baseline_lt"})
_QPS_CONDITIONS = frozenset({"traffic.qps_gt", "traffic.qps_lt"})
_SYSTEM_CONDITIONS = frozenset({
    "system.container_cpu_gt",
    "system.host_cpu_gt",
})


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
            if spec.get("kind") in ("number", "traffic_window", "block_window", "system_window"):
                try:
                    # Keep float thresholds (load / cpu) as float when kind=number.
                    if spec.get("kind") == "number" and key == "threshold":
                        params[key] = float(params[key])
                    else:
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
    if condition_type in _SYSTEM_CONDITIONS:
        window_sec = params.get("window_sec")
        if window_sec is not None and int(window_sec) not in SYSTEM_METRIC_WINDOWS_SEC:
            raise ValueError("不支持的系统负载时间窗口")
        threshold = params.get("threshold")
        if threshold is not None and float(threshold) < 0:
            raise ValueError("阈值不能为负数")
    if condition_type in _QPS_CONDITIONS:
        threshold = params.get("threshold")
        if threshold is not None and float(threshold) < 0:
            raise ValueError("QPS 阈值不能为负数")
    return params
