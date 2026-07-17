"""Validate a unified condition tree against the field catalog.

Condition node forms:
  leaf:  {"field": str, "arg"?: str, "op": str, "value"?: any}
  group: {"logic": "and"|"or", "conditions": [node, ...]}

Raises ValueError with a human-readable (Chinese) message on invalid input.
"""
from __future__ import annotations

from typing import Any

from app.fields.catalog import TRAFFIC, TRAFFIC_COMPARE_MODES, TRAFFIC_RULE_WINDOWS, field_map

_MAP = field_map()
# operators that don't need a value
_NO_VALUE_OPS = {"is_empty", "exists", "key_exists", "key_absent"}
_IP_GROUP_OPS = {"in_ip_group", "not_in_ip_group"}
_TRAFFIC_COMPARES = {m["value"] for m in TRAFFIC_COMPARE_MODES}
_BASELINE_COMPARES = {"baseline_gt", "baseline_lt"}
_MIN_BASELINE_WINDOW_SEC = 300


def _validate_traffic_value(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("全局请求量条件的 value 必须是对象")
    try:
        window_sec = int(value.get("window_sec"))
    except (TypeError, ValueError):
        raise ValueError("全局请求量必须选择时间窗口 window_sec") from None
    if window_sec not in TRAFFIC_RULE_WINDOWS:
        allowed = ", ".join(str(w) for w in TRAFFIC_RULE_WINDOWS)
        raise ValueError(f"不支持的时间窗口 {window_sec}，可选: {allowed}")

    compare = value.get("compare")
    if compare not in _TRAFFIC_COMPARES:
        raise ValueError("全局请求量必须选择比较方式 compare")

    if compare in _BASELINE_COMPARES and window_sec < _MIN_BASELINE_WINDOW_SEC:
        raise ValueError(
            f"基线比较不支持 {window_sec} 秒窗口，请使用 5 分钟或 30 分钟，"
            "或改用绝对值比较"
        )

    if compare in ("abs_gt", "abs_lt"):
        threshold = value.get("threshold")
        if threshold is None or not isinstance(threshold, (int, float)) or threshold < 0:
            raise ValueError("绝对值比较需要提供非负 threshold")
    else:
        percent = value.get("percent")
        if percent is None or not isinstance(percent, (int, float)) or percent < 0:
            raise ValueError("基线比较需要提供非负 percent（百分比）")


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
    if op not in meta["operators"]:
        raise ValueError(f"字段 {field} 不支持操作符 {op}")

    if meta["requires_arg"] and not node.get("arg") and op not in {"key_exists", "key_absent"}:
        # map-type fields need a sub-key (header name / cookie name / json path)
        if node.get("arg") in (None, ""):
            raise ValueError(f"字段 {field} 需要指定子键 arg（如参数名/JSON路径）")

    if op not in _NO_VALUE_OPS and "value" not in node:
        raise ValueError(f"字段 {field} 的操作符 {op} 需要提供 value")

    if meta["value_type"] == TRAFFIC:
        if op != "compare":
            raise ValueError(f"字段 {field} 仅支持 compare 操作符")
        _validate_traffic_value(node.get("value"))
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


def _is_empty_condition(condition: dict | None) -> bool:
    if condition is None or condition == {}:
        return True
    if "conditions" in condition:
        return not (condition.get("conditions") or [])
    return False


def validate_condition(condition: dict | None, *, allow_empty: bool = True) -> dict:
    """Validate and normalize a top-level condition object.

    An empty condition is allowed (matches everything) when allow_empty=True.
    """
    if condition is None or condition == {}:
        if allow_empty:
            return {"logic": "and", "conditions": []}
        raise ValueError("条件不能为空")
    # normalize a bare leaf into a group for consistency
    if "conditions" not in condition and "field" in condition:
        condition = {"logic": "and", "conditions": [condition]}
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
