"""AI Guard apply-mode aliases and protection-mode skill text for the LLM."""
from __future__ import annotations

from app.models.rule import AI_ACTION_MODES

APPLY_MODE_ALIASES = {"auto_block": "auto_handle"}
APPLY_MODES_CANONICAL = ("suggest_only", "auto_observe", "auto_handle")

PROTECTION_MODES: dict[str, dict[str, str]] = {
    "observe": {
        "label": "观察",
        "effect": "只记录命中、不拦截，用于验证规则是否误伤正常请求",
        "when": "证据不足、条件可能偏宽、首次上线新规则、或业务高峰无法确认时",
        "create_when": "几乎所有新规则的默认选择；置信度不够高时必须用观察",
    },
    "block": {
        "label": "拦截",
        "effect": "命中后直接拒绝请求",
        "when": "攻击特征已从多维度交叉验证（IP/UA/参数/频率等至少两类），且几乎不可能命中正常业务",
        "create_when": "高置信度、条件足够窄、已排除搜索引擎/健康检查/回调/静态资源等干扰",
    },
    "js_challenge": {
        "label": "JS 挑战",
        "effect": "要求浏览器执行 JavaScript 后才放行，可挡住大量无头脚本，对真人影响较小",
        "when": "疑似自动化扫描、刷接口、低级 Bot，但尚不能确认全是恶意、不宜直接封禁",
        "create_when": "流量像脚本但可能含真实用户；比拦截更保守，比观察更能止损",
    },
    "slide_captcha": {
        "label": "滑动验证",
        "effect": "弹出滑动人机验证，通过后放行",
        "when": "需要真人交互确认、疑似 CC/撞库/刷量，直接拦截会误伤用户",
        "create_when": "要限制自动化又必须保留真人访问；不要用于纯 API/回调/健康检查路径",
    },
}


def normalize_apply_mode(mode: str | None, *, default: str = "auto_handle") -> str:
    raw = (mode or "").strip() or default
    raw = APPLY_MODE_ALIASES.get(raw, raw)
    if raw not in APPLY_MODES_CANONICAL:
        return default
    return raw


def normalize_action_mode(mode: str | None, *, default: str = "observe") -> str:
    raw = (mode or "").strip() or default
    if raw == "captcha":
        return "js_challenge"
    if raw not in AI_ACTION_MODES:
        return default
    return raw
