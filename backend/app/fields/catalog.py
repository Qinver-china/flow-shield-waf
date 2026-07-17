"""Matching field catalog - the single source of truth for judgment
dimensions. Consumed by:
  1. backend validation (validator.py)
  2. frontend condition editor (via /api/v1/meta/fields)
  3. the OpenResty engine extractor (mirrored in engine/lua/waf/extractor.lua)

Every protection feature (black/white list, exception, rate limit, custom
rule) builds conditions from these fields, so keep this list authoritative.
"""
from __future__ import annotations

# value types
STRING = "string"
NUMBER = "number"
IP = "ip"
ENUM = "enum"
BOOL = "bool"
TRAFFIC = "traffic"

# Rule-configurable global traffic windows (seconds)
TRAFFIC_RULE_WINDOWS = (30, 300, 1800)

# Fixed value options for enum / bool fields (UI + validation hints)
BOOL_OPTIONS: list[dict[str, str]] = [
    {"value": "true", "label": "是"},
    {"value": "false", "label": "否"},
]

FIELD_OPTIONS: dict[str, list[dict[str, str]]] = {
    "http.method": [
        {"value": "GET", "label": "GET"},
        {"value": "POST", "label": "POST"},
        {"value": "PUT", "label": "PUT"},
        {"value": "DELETE", "label": "DELETE"},
        {"value": "PATCH", "label": "PATCH"},
        {"value": "HEAD", "label": "HEAD"},
        {"value": "OPTIONS", "label": "OPTIONS"},
        {"value": "CONNECT", "label": "CONNECT"},
        {"value": "TRACE", "label": "TRACE"},
    ],
    "net.scheme": [
        {"value": "http", "label": "HTTP"},
        {"value": "https", "label": "HTTPS"},
    ],
    "http.version": [
        {"value": "1.0", "label": "HTTP/1.0"},
        {"value": "1.1", "label": "HTTP/1.1"},
        {"value": "2.0", "label": "HTTP/2"},
        {"value": "3.0", "label": "HTTP/3"},
    ],
    "geo.ip_type": [
        {"value": "residential", "label": "家庭宽带"},
        {"value": "business", "label": "商业/企业"},
        {"value": "hosting", "label": "机房/托管"},
        {"value": "mobile", "label": "移动网络"},
        {"value": "education", "label": "教育网"},
        {"value": "government", "label": "政府"},
    ],
    "traffic.global": [
        {"value": "30", "label": "30 秒"},
        {"value": "300", "label": "5 分钟"},
        {"value": "1800", "label": "30 分钟"},
    ],
}

TRAFFIC_COMPARE_MODES: list[dict[str, str]] = [
    {"value": "abs_gt", "label": "请求量高于"},
    {"value": "abs_lt", "label": "请求量低于"},
    {"value": "baseline_gt", "label": "高于基线百分比"},
    {"value": "baseline_lt", "label": "低于基线百分比"},
]

# operators grouped by value type
OPERATORS_BY_TYPE: dict[str, list[str]] = {
    STRING: [
        "equals", "not_equals", "contains", "not_contains", "starts_with",
        "ends_with", "regex", "in_list", "not_in", "is_empty", "exists",
        "len_gt", "len_lt",
    ],
    NUMBER: ["eq", "neq", "gt", "gte", "lt", "lte", "between"],
    IP: ["eq", "in_cidr", "in_list", "in_ip_group", "not_in_ip_group", "geo_in", "exists"],
    ENUM: ["eq", "neq", "in_list"],
    BOOL: ["eq"],
    TRAFFIC: ["compare"],
}

# human labels for operators (for the frontend)
OPERATORS: dict[str, str] = {
    "equals": "等于",
    "not_equals": "不等于",
    "contains": "包含字符",
    "not_contains": "不包含字符",
    "starts_with": "以…开头",
    "ends_with": "以…结尾",
    "regex": "正则匹配",
    "in_list": "包含",
    "not_in": "不包含",
    "is_empty": "为空",
    "exists": "存在",
    "len_gt": "长度大于",
    "len_lt": "长度小于",
    "eq": "等于",
    "neq": "不等于",
    "gt": "大于",
    "gte": "大于等于",
    "lt": "小于",
    "lte": "小于等于",
    "between": "介于",
    "in_cidr": "在网段中",
    "in_ip_group": "包含 IP 组",
    "not_in_ip_group": "不包含 IP 组",
    "geo_in": "属于地区",
    "key_exists": "键存在",
    "key_absent": "键不存在",
    "compare": "流量比较",
}


def _f(key, label, category, value_type, requires_arg=False, extra_ops=None):
    ops = list(OPERATORS_BY_TYPE[value_type])
    if requires_arg:
        ops += ["key_exists", "key_absent"]
    if extra_ops:
        ops += [o for o in extra_ops if o not in ops]
    return {
        "key": key,
        "label": label,
        "category": category,
        "value_type": value_type,
        "requires_arg": requires_arg,
        "operators": ops,
    }


# ordered catalog
FIELDS: list[dict] = [
    # client & network
    _f("ip.src", "客户端 IP", "客户端与网络", IP),
    _f("ip.src.is_private", "IP 是否内网", "客户端与网络", BOOL),
    _f("net.src_port", "客户端端口", "客户端与网络", NUMBER),
    _f("net.dst_port", "服务端口", "客户端与网络", NUMBER),
    _f("net.scheme", "协议", "客户端与网络", ENUM),
    _f("http.version", "HTTP 版本", "客户端与网络", ENUM),
    # geo / threat intel
    _f("geo.country", "IP 国家/地区", "地理位置与情报", STRING),
    _f("geo.region", "IP 省/州", "地理位置与情报", STRING),
    _f("geo.city", "IP 城市", "地理位置与情报", STRING),
    _f("geo.asn", "IP ASN", "地理位置与情报", NUMBER),
    _f("geo.isp", "运营商 ISP", "地理位置与情报", STRING),
    _f("geo.ip_type", "IP 类型", "地理位置与情报", ENUM),
    # request line
    _f("http.method", "请求方法", "请求行", ENUM),
    _f("http.host", "请求域名", "请求行", STRING),
    _f("http.url", "完整 URL", "请求行", STRING),
    _f("http.request_uri", "原始请求行", "请求行", STRING),
    # url / path
    _f("http.uri.path", "请求路径", "URL 与路径", STRING),
    _f("http.uri.segment", "路径段", "URL 与路径", STRING, requires_arg=True),
    _f("http.uri.ext", "文件后缀", "URL 与路径", STRING),
    _f("http.uri.depth", "路径深度", "URL 与路径", NUMBER),
    _f("http.uri.query", "原始查询串", "URL 与路径", STRING),
    # query args
    _f("http.query", "查询参数", "查询参数", STRING, requires_arg=True),
    _f("http.query.count", "查询参数个数", "查询参数", NUMBER),
    # headers
    _f("http.header", "请求头", "请求头", STRING, requires_arg=True),
    _f("http.header.count", "请求头数量", "请求头", NUMBER),
    _f("http.ua", "User-Agent", "请求头", STRING),
    _f("http.referer", "Referer", "请求头", STRING),
    _f("http.content_type", "Content-Type", "请求头", STRING),
    _f("http.content_length", "Content-Length", "请求头", NUMBER),
    _f("http.accept", "Accept", "请求头", STRING),
    _f("http.accept_language", "Accept-Language", "请求头", STRING),
    _f("http.accept_encoding", "Accept-Encoding", "请求头", STRING),
    _f("http.origin", "Origin", "请求头", STRING),
    _f("http.xff", "X-Forwarded-For", "请求头", STRING),
    _f("http.range", "Range", "请求头", STRING),
    _f("http.has_auth", "是否带 Authorization", "请求头", BOOL),
    # cookies
    _f("http.cookie", "Cookie 参数", "Cookie", STRING, requires_arg=True),
    _f("http.cookie_raw", "原始 Cookie", "Cookie", STRING),
    _f("http.cookie.count", "Cookie 个数", "Cookie", NUMBER),
    # body
    _f("http.body.raw", "原始请求体", "请求体", STRING),
    _f("http.body.size", "请求体大小", "请求体", NUMBER),
    _f("http.body.form", "表单参数", "请求体", STRING, requires_arg=True),
    _f("http.body.json", "JSON 字段", "请求体", STRING, requires_arg=True),
    _f("http.upload.filename", "上传文件名", "请求体", STRING),
    _f("http.upload.ext", "上传文件后缀", "请求体", STRING),
    # tls
    _f("tls.version", "TLS 版本", "TLS 与指纹", STRING),
    _f("tls.cipher", "TLS 加密套件", "TLS 与指纹", STRING),
    _f("tls.sni", "SNI", "TLS 与指纹", STRING),
    _f("tls.ja3", "JA3 指纹", "TLS 与指纹", STRING),
    # derived
    _f("derived.args_count", "参数总数", "派生维度", NUMBER),
    _f("derived.time.hour", "当前小时", "派生维度", NUMBER),
    _f("derived.time.weekday", "星期几", "派生维度", NUMBER),
    _f("derived.fingerprint", "请求指纹", "派生维度", STRING),
    # traffic intelligence
    {
        "key": "traffic.global",
        "label": "全局请求量",
        "category": "流量与智能",
        "value_type": TRAFFIC,
        "requires_arg": False,
        "operators": ["compare"],
        "compare_modes": TRAFFIC_COMPARE_MODES,
    },
]


def options_for_field(field: dict) -> list[dict[str, str]] | None:
    if field["value_type"] == BOOL:
        return BOOL_OPTIONS
    if field["value_type"] == ENUM:
        return FIELD_OPTIONS.get(field["key"])
    return None


def field_map() -> dict[str, dict]:
    return {f["key"]: f for f in FIELDS}


def catalog_for_frontend() -> dict:
    """Grouped catalog + operator labels for the condition editor."""
    categories: dict[str, list[dict]] = {}
    for f in FIELDS:
        entry = dict(f)
        opts = options_for_field(f)
        if opts:
            entry["options"] = opts
        if f.get("compare_modes"):
            entry["compare_modes"] = f["compare_modes"]
        categories.setdefault(f["category"], []).append(entry)
    return {
        "categories": [
            {"name": name, "fields": fields} for name, fields in categories.items()
        ],
        "operators": OPERATORS,
        "operators_by_type": OPERATORS_BY_TYPE,
    }


def catalog_compact_for_llm() -> dict:
    """Lightweight field catalog for LLM prompts (no UI option lists)."""
    return {
        "fields": [
            {
                "key": f["key"],
                "label": f["label"],
                "category": f["category"],
                "value_type": f["value_type"],
                "requires_arg": f.get("requires_arg", False),
                "operators": f.get("operators")
                or OPERATORS_BY_TYPE.get(f["value_type"], []),
            }
            for f in FIELDS
        ],
        "operators_by_type": OPERATORS_BY_TYPE,
    }
