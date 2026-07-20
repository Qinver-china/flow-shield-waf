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
    "TR": "土耳其",
    "PL": "波兰",
    "UA": "乌克兰",
    "MX": "墨西哥",
    "AR": "阿根廷",
    "ZA": "南非",
    "NZ": "新西兰",
    "IE": "爱尔兰",
    "BE": "比利时",
    "AT": "奥地利",
    "PT": "葡萄牙",
    "FI": "芬兰",
    "NO": "挪威",
    "DK": "丹麦",
    "CZ": "捷克",
    "RO": "罗马尼亚",
    "HU": "匈牙利",
    "IL": "以色列",
    "SA": "沙特阿拉伯",
    "PK": "巴基斯坦",
    "BD": "孟加拉国",
    "NG": "尼日利亚",
    "EG": "埃及",
    "KZ": "哈萨克斯坦",
    "UZ": "乌兹别克斯坦",
    "MM": "缅甸",
    "KH": "柬埔寨",
    "LA": "老挝",
    "NP": "尼泊尔",
    "LK": "斯里兰卡",
    "IQ": "伊拉克",
    "IR": "伊朗",
    "UNKNOWN": "未知",
    "XX": "未知",
}

GEO_CN_REGION_LABELS: dict[str, str] = {
    "BJ": "北京",
    "TJ": "天津",
    "HE": "河北",
    "SX": "山西",
    "NM": "内蒙古",
    "LN": "辽宁",
    "JL": "吉林",
    "HL": "黑龙江",
    "SH": "上海",
    "JS": "江苏",
    "ZJ": "浙江",
    "AH": "安徽",
    "FJ": "福建",
    "JX": "江西",
    "SD": "山东",
    "HA": "河南",
    "HB": "湖北",
    "HN": "湖南",
    "GD": "广东",
    "GX": "广西",
    "HI": "海南",
    "CQ": "重庆",
    "SC": "四川",
    "GZ": "贵州",
    "YN": "云南",
    "XZ": "西藏",
    "SN": "陕西",
    "GS": "甘肃",
    "QH": "青海",
    "NX": "宁夏",
    "XJ": "新疆",
}


def format_geo_country(code: str | None) -> str:
    c = (code or "").strip().upper()
    if not c:
        return ""
    name = GEO_COUNTRY_LABELS.get(c)
    return f"{name} ({c})" if name else c


# Common MaxMind ASN org-name keywords → Chinese labels (case-insensitive substring).
# Matching still uses the raw organization string; this is display-only.
GEO_ISP_LABELS: list[tuple[str, str]] = [
    ("china mobile international", "中国移动国际"),
    ("chinanet", "中国电信"),
    ("china telecom", "中国电信"),
    ("china-telecom", "中国电信"),
    ("china unicom", "中国联通"),
    ("chinaunicom", "中国联通"),
    ("china-unicom", "中国联通"),
    ("china mobile", "中国移动"),
    ("chinamobile", "中国移动"),
    ("cmnet", "中国移动"),
    ("cmcc", "中国移动"),
    ("cernet", "教育网 CERNET"),
    ("cstnet", "中科院 CSTNET"),
    ("drpeng", "鹏博士"),
    ("wasu", "华数"),
    ("gehua", "歌华有线"),
    ("alibaba", "阿里云"),
    ("aliyun", "阿里云"),
    ("taobao", "阿里云"),
    ("tencent", "腾讯云"),
    ("huawei", "华为云"),
    ("baidu", "百度云"),
    ("bytedance", "字节跳动"),
    ("byteplus", "火山引擎"),
    ("volcengine", "火山引擎"),
    ("jd.com", "京东云"),
    ("jingdong", "京东云"),
    ("kingsoft", "金山云"),
    ("ucloud", "UCloud"),
    ("qingcloud", "青云"),
    ("hkt", "香港电讯"),
    ("pccw", "电讯盈科"),
    ("chunghwa", "中华电信"),
    ("far eastone", "远传电信"),
    ("taiwan mobile", "台湾大哥大"),
    ("amazon", "亚马逊 AWS"),
    ("google", "谷歌云"),
    ("microsoft", "微软 Azure"),
    ("azure", "微软 Azure"),
    ("cloudflare", "Cloudflare"),
    ("akamai", "Akamai"),
    ("fastly", "Fastly"),
    ("digitalocean", "DigitalOcean"),
    ("linode", "Linode"),
    ("vultr", "Vultr"),
    ("ovh", "OVH"),
    ("hetzner", "Hetzner"),
    ("oracle", "甲骨文云"),
    ("softlayer", "IBM SoftLayer"),
    ("ibm", "IBM 云"),
    ("leaseweb", "Leaseweb"),
    ("contabo", "Contabo"),
    ("m247", "M247"),
    ("cogent", "Cogent"),
    ("lumen", "Lumen"),
    ("level 3", "Level3"),
    ("level3", "Level3"),
    ("meta platforms", "Meta"),
    ("facebook", "Meta"),
    ("apple", "Apple"),
    ("github", "GitHub"),
]

# Filter / rule hints: value ≈ common MaxMind organization fragments
GEO_ISP_SELECT_HINTS: list[dict[str, str]] = [
    {"value": "China Telecom", "label": "中国电信 (China Telecom)"},
    {"value": "China Unicom", "label": "中国联通 (China Unicom)"},
    {"value": "China Mobile", "label": "中国移动 (China Mobile)"},
    {"value": "CERNET", "label": "教育网 (CERNET)"},
    {"value": "Alibaba", "label": "阿里云 (Alibaba)"},
    {"value": "Tencent", "label": "腾讯云 (Tencent)"},
    {"value": "Huawei", "label": "华为云 (Huawei)"},
    {"value": "Amazon.com, Inc.", "label": "亚马逊 AWS (Amazon.com, Inc.)"},
    {"value": "GOOGLE", "label": "谷歌云 (GOOGLE)"},
    {"value": "MICROSOFT-CORP-MSN-AS-BLOCK", "label": "微软 Azure (Microsoft)"},
    {"value": "CLOUDFLARENET", "label": "Cloudflare (CLOUDFLARENET)"},
    {"value": "AKAMAI", "label": "Akamai"},
    {"value": "DIGITALOCEAN", "label": "DigitalOcean"},
    {"value": "Hetzner Online GmbH", "label": "Hetzner"},
    {"value": "OVH SAS", "label": "OVH"},
]


def format_geo_isp(isp: str | None) -> str:
    raw = (isp or "").strip()
    if not raw:
        return ""
    lower = raw.lower()
    for match, label in GEO_ISP_LABELS:
        if match in lower:
            return f"{label} ({raw})"
    return raw


def geo_country_field_options() -> list[dict[str, str]]:
    items = [
        {"value": code, "label": f"{name} ({code})"}
        for code, name in GEO_COUNTRY_LABELS.items()
        if code not in ("UNKNOWN", "XX")
    ]
    items.sort(key=lambda x: x["label"])
    return items


def geo_cn_region_field_options() -> list[dict[str, str]]:
    items = [
        {"value": code, "label": f"{name} ({code})"}
        for code, name in GEO_CN_REGION_LABELS.items()
    ]
    items.sort(key=lambda x: x["label"])
    return items


def geo_isp_field_options() -> list[dict[str, str]]:
    return list(GEO_ISP_SELECT_HINTS)


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
        return format_geo_country(code) or raw_label or code
    if dimension == "geo_isp":
        return format_geo_isp(key or raw_label) or raw_label or key
    if dimension == "ua":
        return raw_label or key
    if dimension == "full_url":
        return raw_label or key
    if dimension in ("request_uri", "uri_query"):
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
