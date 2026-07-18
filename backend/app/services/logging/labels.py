"""Human-readable Chinese labels for log statistics dimension values."""
from __future__ import annotations

SOURCE_LABELS: dict[str, str] = {
    "ratelimit": "速率防护",
    "rule": "自定义规则",
    "blacklist": "黑名单",
    "whitelist": "白名单",
    "bot": "Bot 库",
}

_BOT_CATEGORY_LABELS: dict[str, str] = {}


def set_bot_category_labels(labels: dict[str, str]) -> None:
    global _BOT_CATEGORY_LABELS
    _BOT_CATEGORY_LABELS = dict(labels)

MODE_LABELS: dict[str, str] = {
    "observe": "观察",
    "block": "拦截",
    "captcha": "数学计算验证",
    "js_challenge": "JS 挑战",
    "slide_captcha": "滑动验证",
    "unknown": "未知",
}

LOG_TYPE_LABELS: dict[str, str] = {
    "protection": "防护命中",
    "access-control": "访问控制",
    "audit": "审计",
}

# Common ISO 3166-1 alpha-2 codes (fallback to raw code)
GEO_COUNTRY_LABELS: dict[str, str] = {
    "CN": "中国",
    "US": "美国",
    "HK": "中国香港",
    "TW": "中国台湾",
    "MO": "中国澳门",
    "JP": "日本",
    "KR": "韩国",
    "SG": "新加坡",
    "GB": "英国",
    "DE": "德国",
    "FR": "法国",
    "RU": "俄罗斯",
    "IN": "印度",
    "AU": "澳大利亚",
    "CA": "加拿大",
    "NL": "荷兰",
    "VN": "越南",
    "TH": "泰国",
    "MY": "马来西亚",
    "ID": "印度尼西亚",
    "PH": "菲律宾",
    "BR": "巴西",
    "IT": "意大利",
    "ES": "西班牙",
    "SE": "瑞典",
    "CH": "瑞士",
    "AE": "阿联酋",
    "UNKNOWN": "未知",
    "XX": "未知",
}


def _lookup(mapping: dict[str, str], value: str | None) -> str | None:
    if value is None:
        return None
    return mapping.get(str(value).strip()) or mapping.get(str(value).strip().lower())


def format_rule_stats_label(
    *,
    rule_id: int | str,
    rule_name: str | None,
    source: str | None = None,
) -> str:
    """Format a grouped hit-rule row, prefixing localized source in brackets."""
    rid = str(rule_id)
    name = (rule_name or "").strip() or f"规则 #{rid}"
    body = f"{name} (#{rid})"
    if not source:
        return body
    src = _lookup(SOURCE_LABELS, source) or source
    return f"[{src}]{body}"


def format_dimension_label(
    dimension: str,
    key: str,
    raw_label: str,
    *,
    site_name: str | None = None,
    site_domain: str | None = None,
) -> str:
    """Convert a grouped stats row label to Chinese where applicable."""
    if key == "none" or raw_label == "（空）":
        return "（空）"

    if dimension == "source":
        return _lookup(SOURCE_LABELS, key) or _lookup(SOURCE_LABELS, raw_label) or raw_label
    if dimension in ("mode", "action"):
        return _lookup(MODE_LABELS, key) or _lookup(MODE_LABELS, raw_label) or raw_label
    if dimension == "log_type":
        return _lookup(LOG_TYPE_LABELS, key) or _lookup(LOG_TYPE_LABELS, raw_label) or raw_label
    if dimension == "blocked":
        return "已拦截" if key == "true" else "已放行"
    if dimension == "geo_country":
        code = (key or raw_label or "").upper()
        return GEO_COUNTRY_LABELS.get(code, raw_label or code)
    if dimension == "ua":
        return raw_label or key
    if dimension == "full_url":
        return raw_label or key
    if dimension == "bot_category":
        return _BOT_CATEGORY_LABELS.get(key, raw_label or key)
    if dimension == "site_id":
        if site_name and site_domain:
            return f"{site_name} ({site_domain})"
        if site_name:
            return f"{site_name} (#{key})"
        if site_domain:
            return f"{site_domain} (#{key})"
        return f"站点 #{key}" if key != "none" else "（空）"

    return raw_label
