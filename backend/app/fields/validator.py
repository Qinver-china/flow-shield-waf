"""Validate a unified condition tree against the field catalog.

Condition node forms:
  leaf:  {"field": str, "arg"?: str, "op": str, "value"?: any}
  group: {"logic": "and"|"or", "conditions": [node, ...]}

Raises ValueError with a human-readable (Chinese) message on invalid input.
"""
from __future__ import annotations

from typing import Any

from app.constants.traffic_windows import TRAFFIC_BASELINE_MIN_WINDOW_SEC
from app.constants.system_metrics import SYSTEM_METRIC_WINDOWS_SEC
from app.fields.catalog import (
    SYSTEM,
    SYSTEM_CPU_COMPARE_MODES,
    TRAFFIC,
    TRAFFIC_COMPARE_MODES,
    TRAFFIC_RULE_WINDOWS,
    field_map,
)

_MAP = field_map()
# operators that don't need a value
_NO_VALUE_OPS = {"is_empty", "exists", "key_exists", "key_absent"}
_IP_GROUP_OPS = {"in_ip_group", "not_in_ip_group"}
# LLM / mixed-type aliases: enum uses eq/neq, string uses equals/not_equals
_OP_ALIASES = {
    "equals": "eq",
    "eq": "equals",
    "not_equals": "neq",
    "neq": "not_equals",
}
_TRAFFIC_COMPARES = {m["value"] for m in TRAFFIC_COMPARE_MODES}
_SYSTEM_CPU_COMPARES = {m["value"] for m in SYSTEM_CPU_COMPARE_MODES}
_BASELINE_COMPARES = {"baseline_gt", "baseline_lt"}
_QPS_COMPARES = {"qps_gt", "qps_lt"}
_TRAFFIC_FIELDS = {"traffic.global", "traffic.site"}
_SYSTEM_CPU_FIELDS = {"system.cpu"}
_TRAFFIC_COMPARE_OPS = {
    "gt": "abs_gt",
    "gte": "abs_gt",
    ">": "abs_gt",
    ">=": "abs_gt",
    "lt": "abs_lt",
    "lte": "abs_lt",
    "<": "abs_lt",
    "<=": "abs_lt",
    "qps_gt": "qps_gt",
    "qps_lt": "qps_lt",
    "abs_gt": "abs_gt",
    "abs_lt": "abs_lt",
    "baseline_gt": "baseline_gt",
    "baseline_lt": "baseline_lt",
}


def _normalize_traffic_leaf(node: dict[str, Any]) -> dict[str, Any]:
    """Map LLM-friendly traffic aliases (e.g. traffic.global.request_count) to catalog keys."""
    field = node.get("field")
    if not isinstance(field, str):
        return node
    if field in _TRAFFIC_FIELDS:
        return node

    base: str | None = None
    metric = ""
    if field.startswith("traffic.global."):
        base = "traffic.global"
        metric = field[len("traffic.global.") :]
    elif field.startswith("traffic.site."):
        base = "traffic.site"
        metric = field[len("traffic.site.") :]
    if base is None:
        return node

    out = dict(node)
    out["field"] = base
    if out.get("op") == "compare" and isinstance(out.get("value"), dict):
        return out

    op = str(out.get("op") or "")
    raw_value = out.get("value")
    prefer_qps = metric in ("qps", "rps") or op in ("qps_gt", "qps_lt")
    if op in _TRAFFIC_COMPARE_OPS:
        compare = _TRAFFIC_COMPARE_OPS[op]
    else:
        compare = "qps_gt" if prefer_qps else "abs_gt"

    if isinstance(raw_value, dict):
        tv = dict(raw_value)
        tv.setdefault("window_sec", 300)
        tv.setdefault("compare", compare)
        if compare in ("abs_gt", "abs_lt", "qps_gt", "qps_lt"):
            if "threshold" not in tv and "value" in tv:
                tv["threshold"] = tv.pop("value")
        elif compare in ("baseline_gt", "baseline_lt"):
            if "percent" not in tv and "value" in tv:
                tv["percent"] = tv.pop("value")
    elif isinstance(raw_value, (int, float)):
        if compare.startswith("baseline"):
            tv = {"window_sec": 300, "compare": compare, "percent": raw_value}
        else:
            tv = {"window_sec": 300, "compare": compare, "threshold": raw_value}
    else:
        return out

    out["op"] = "compare"
    out["value"] = tv
    return out


def _validate_traffic_value(value: Any, field: str) -> None:
    if not isinstance(value, dict):
        raise ValueError("请求量条件的 value 必须是对象")
    try:
        window_sec = int(value.get("window_sec"))
    except (TypeError, ValueError):
        raise ValueError("请求量必须选择时间窗口 window_sec") from None
    if window_sec not in TRAFFIC_RULE_WINDOWS:
        allowed = ", ".join(str(w) for w in TRAFFIC_RULE_WINDOWS)
        raise ValueError(f"不支持的时间窗口 {window_sec}，可选: {allowed}")

    compare = value.get("compare")
    if compare not in _TRAFFIC_COMPARES:
        raise ValueError("请求量必须选择比较方式 compare")

    if compare in _BASELINE_COMPARES and window_sec < TRAFFIC_BASELINE_MIN_WINDOW_SEC:
        raise ValueError(
            f"基线比较不支持 {window_sec} 秒窗口，请使用 5 分钟或 30 分钟，"
            "或改用绝对值 / QPS 比较"
        )

    if compare in ("abs_gt", "abs_lt", *_QPS_COMPARES):
        threshold = value.get("threshold")
        if threshold is None or not isinstance(threshold, (int, float)) or threshold < 0:
            label = "QPS" if compare in _QPS_COMPARES else "请求量"
            raise ValueError(f"{label}比较需要提供非负 threshold")
    else:
        percent = value.get("percent")
        if percent is None or not isinstance(percent, (int, float)) or percent < 0:
            raise ValueError("基线比较需要提供非负 percent（百分比）")

    if field == "traffic.site" and compare in _BASELINE_COMPARES:
        # site baseline is supported; no extra validation needed
        pass


def _validate_system_cpu_value(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("系统 CPU/负载条件的 value 必须是对象")
    try:
        window_sec = int(value.get("window_sec"))
    except (TypeError, ValueError):
        raise ValueError("系统 CPU/负载必须选择时间窗口 window_sec") from None
    if window_sec not in SYSTEM_METRIC_WINDOWS_SEC:
        allowed = ", ".join(str(w) for w in SYSTEM_METRIC_WINDOWS_SEC)
        raise ValueError(f"不支持的时间窗口 {window_sec}，可选: {allowed}")

    compare = value.get("compare")
    if compare not in _SYSTEM_CPU_COMPARES:
        raise ValueError("系统 CPU/负载必须选择比较方式 compare")

    threshold = value.get("threshold")
    if threshold is None or not isinstance(threshold, (int, float)) or threshold < 0:
        raise ValueError("系统 CPU/负载比较需要提供非负 threshold")


def _normalize_op(op: str, allowed: list[str] | tuple[str, ...] | set[str]) -> str | None:
    """Return op if allowed, or its alias if that is allowed; else None."""
    if op in allowed:
        return op
    alias = _OP_ALIASES.get(op)
    if alias and alias in allowed:
        return alias
    return None


def _validate_leaf(node: dict[str, Any]) -> None:
    field = node.get("field")
    if not field:
        raise ValueError("条件缺少 field 字段")
    meta = _MAP.get(field)
    if not meta:
        raise ValueError(f"未知匹配字段: {field}")

    op = node.get("op")
    if not op:
        raise ValueError(f"字段 {field} 缺少操作符 op")
    allowed = meta["operators"]
    normalized_op = _normalize_op(str(op), allowed)
    if normalized_op is None:
        raise ValueError(f"字段 {field} 不支持操作符 {op}")
    if normalized_op != op:
        node["op"] = normalized_op
        op = normalized_op

    if meta["requires_arg"] and not node.get("arg") and op not in {"key_exists", "key_absent"}:
        # map-type fields need a sub-key (header name / cookie name / json path)
        if node.get("arg") in (None, ""):
            raise ValueError(f"字段 {field} 需要指定子键 arg（如参数名/JSON路径）")

    if op not in _NO_VALUE_OPS and "value" not in node:
        raise ValueError(f"字段 {field} 的操作符 {op} 需要提供 value")

    if meta["value_type"] == TRAFFIC:
        if op != "compare":
            raise ValueError(f"字段 {field} 仅支持 compare 操作符")
        if field not in _TRAFFIC_FIELDS:
            raise ValueError(f"未知请求量字段: {field}")
        _validate_traffic_value(node.get("value"), field)
        return

    if meta["value_type"] == SYSTEM:
        if op != "compare":
            raise ValueError(f"字段 {field} 仅支持 compare 操作符")
        if field not in _SYSTEM_CPU_FIELDS:
            raise ValueError(f"未知系统指标字段: {field}")
        _validate_system_cpu_value(node.get("value"))
        return

    if op == "between":
        val = node.get("value")
        if not isinstance(val, (list, tuple)) or len(val) != 2:
            raise ValueError("between 操作符的 value 必须是长度为 2 的数组")

    if op in _IP_GROUP_OPS:
        val = node.get("value")
        if not isinstance(val, (list, tuple)) or not val:
            raise ValueError(f"操作符 {op} 需要选择至少一个 IP 组")
        for item in val:
            if not isinstance(item, int) or item <= 0:
                raise ValueError("IP 组 ID 必须是正整数")


def _normalize_condition_shape(node: Any) -> Any:
    """Accept LLM-friendly all/any aliases as logic/conditions groups."""
    if not isinstance(node, dict):
        return node
    if "conditions" in node:
        out = dict(node)
        conds = out.get("conditions")
        if isinstance(conds, list):
            out["conditions"] = [_normalize_condition_shape(c) for c in conds]
        return out
    if "all" in node:
        items = node.get("all")
        if not isinstance(items, list):
            raise ValueError("all 必须是数组")
        return {"logic": "and", "conditions": [_normalize_condition_shape(c) for c in items]}
    if "any" in node:
        items = node.get("any")
        if not isinstance(items, list):
            raise ValueError("any 必须是数组")
        return {"logic": "or", "conditions": [_normalize_condition_shape(c) for c in items]}
    if "field" in node:
        return _normalize_traffic_leaf(node)
    return node


def _validate_node(node: Any, depth: int = 0) -> None:
    if depth > 10:
        raise ValueError("条件嵌套层级过深")
    if not isinstance(node, dict):
        raise ValueError("条件节点必须是对象")
    if "conditions" in node:
        logic = (node.get("logic") or "and").lower()
        if logic not in ("and", "or"):
            raise ValueError("logic 只能是 and 或 or")
        conds = node.get("conditions")
        if not isinstance(conds, list):
            raise ValueError("conditions 必须是数组")
        for child in conds:
            _validate_node(child, depth + 1)
    else:
        _validate_leaf(node)


def _count_leaf_conditions(node: Any) -> int:
    if not isinstance(node, dict):
        return 0
    if node.get("field"):
        return 1
    conds = node.get("conditions")
    if isinstance(conds, list):
        return sum(_count_leaf_conditions(child) for child in conds)
    return 0


def has_meaningful_conditions(condition: dict | None) -> bool:
    """Return True when the tree contains at least one leaf condition."""
    return _count_leaf_conditions(condition) > 0


def _is_empty_condition(condition: dict | None) -> bool:
    return not has_meaningful_conditions(condition)


def validate_condition(condition: dict | None, *, allow_empty: bool = True) -> dict:
    """Validate and normalize a top-level condition object.

    An empty condition is allowed (matches everything) when allow_empty=True.
    """
    if condition is None or condition == {}:
        if allow_empty:
            return {"logic": "and", "conditions": []}
        raise ValueError("条件不能为空")
    condition = _normalize_condition_shape(condition)
    # normalize a bare leaf into a group for consistency
    if "conditions" not in condition and "field" in condition:
        condition = {"logic": "and", "conditions": [condition]}
    if not allow_empty and _is_empty_condition(condition):
        raise ValueError("条件不能为空")
    _validate_node(condition)
    return condition


async def validate_condition_with_refs(
    db,
    condition: dict | None,
    *,
    allow_empty: bool = True,
) -> dict:
    from app.services.reference_validation import validate_condition_references

    normalized = validate_condition(condition, allow_empty=allow_empty)
    await validate_condition_references(db, normalized)
    return normalized
