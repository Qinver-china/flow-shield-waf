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
SYSTEM = "system"

from app.constants.system_metrics import SYSTEM_METRIC_WINDOWS_SEC, system_metric_window_options
from app.constants.traffic_windows import (
    TRAFFIC_BASELINE_MIN_WINDOW_SEC,
    TRAFFIC_WINDOWS_SEC,
    traffic_window_options,
)
from app.services.logging.labels import (
    geo_asn_field_options,
    geo_city_field_options,
    geo_country_field_options,
    geo_isp_field_options,
    geo_region_field_options,
)

TRAFFIC_RULE_WINDOWS = TRAFFIC_WINDOWS_SEC

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
    "geo.country": geo_country_field_options(),
    "geo.region": geo_region_field_options(),
    "geo.city": geo_city_field_options(),
    "geo.asn": geo_asn_field_options(),
    "geo.isp": geo_isp_field_options(),
    "ua.family": [
        {"value": "browser", "label": "浏览器"},
        {"value": "bot", "label": "Bot"},
    ],
    "traffic.global": traffic_window_options(as_string=True),
    "traffic.site": traffic_window_options(as_string=True),
    "traffic.origin_global": traffic_window_options(as_string=True),
    "traffic.origin_site": traffic_window_options(as_string=True),
    "system.cpu": system_metric_window_options(as_string=True),
}

TRAFFIC_COMPARE_MODES: list[dict[str, str]] = [
    {"value": "abs_gt", "label": "请求量高于"},
    {"value": "abs_lt", "label": "请求量低于"},
    {"value": "qps_gt", "label": "QPS 高于"},
    {"value": "qps_lt", "label": "QPS 低于"},
    {"value": "baseline_gt", "label": "高于基线百分比"},
    {"value": "baseline_lt", "label": "低于基线百分比"},
]

ORIGIN_TRAFFIC_COMPARE_MODES: list[dict[str, str]] = [
    {"value": "abs_gt", "label": "回源请求量高于"},
    {"value": "abs_lt", "label": "回源请求量低于"},
    {"value": "qps_gt", "label": "回源 QPS 高于"},
    {"value": "qps_lt", "label": "回源 QPS 低于"},
]

SYSTEM_CPU_COMPARE_MODES: list[dict[str, str]] = [
    {"value": "container_cpu_gt", "label": "容器CPU%高于"},
    {"value": "container_cpu_lt", "label": "容器CPU%低于"},
    {"value": "host_cpu_gt", "label": "宿主机CPU%高于"},
    {"value": "host_cpu_lt", "label": "宿主机CPU%低于"},
]

_TRAFFIC_FIELD_DEF = {
    "value_type": TRAFFIC,
    "requires_arg": False,
    "operators": ["compare"],
    "compare_modes": TRAFFIC_COMPARE_MODES,
}

_ORIGIN_TRAFFIC_FIELD_DEF = {
    "value_type": TRAFFIC,
    "requires_arg": False,
    "operators": ["compare"],
    "compare_modes": ORIGIN_TRAFFIC_COMPARE_MODES,
}

_SYSTEM_CPU_FIELD_DEF = {
    "value_type": SYSTEM,
    "requires_arg": False,
    "operators": ["compare"],
    "compare_modes": SYSTEM_CPU_COMPARE_MODES,
}

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
    SYSTEM: ["compare"],
}

# human labels for operators (for the frontend)
OPERATORS: dict[str, str] = {
    "equals": "等于",
    "not_equals": "不等于",
    "contains": "包含字符串",
    "not_contains": "排除字符串",
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
    "compare": "比较",
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


# ordered category names for the condition editor (and log dimension UI alignment)
CATEGORY_ORDER: list[str] = [
    "网络与地理",
    "URL 与路径",
    "HTTP 请求",
    "客户端识别",
    "时间与流量",
]

# ordered catalog
FIELDS: list[dict] = [
    # client & network
    _f("ip.src", "客户端 IP", "网络与地理", IP),
    _f("ip.src.is_private", "IP 是否内网", "网络与地理", BOOL),
    _f("net.src_port", "客户端端口", "网络与地理", NUMBER),
    _f("net.dst_port", "服务端口", "网络与地理", NUMBER),
    _f("net.scheme", "协议", "网络与地理", ENUM),
    _f("http.version", "HTTP 版本", "网络与地理", ENUM),
    # geo / threat intel
    _f("geo.country", "IP 国家/地区", "网络与地理", ENUM),
    _f("geo.region", "IP 省/州", "网络与地理", STRING),
    _f("geo.city", "IP 城市", "网络与地理", STRING),
    _f("geo.asn", "IP ASN", "网络与地理", NUMBER),
    _f("geo.isp", "运营商 ISP", "网络与地理", STRING),
    # url / path
    _f("http.host", "请求域名", "URL 与路径", STRING),
    _f("http.url", "完整 URL", "URL 与路径", STRING),
    _f("http.request_uri", "原始请求行", "URL 与路径", STRING),
    _f("http.uri.path", "请求路径", "URL 与路径", STRING),
    _f("http.uri.segment", "路径段", "URL 与路径", STRING, requires_arg=True),
    _f("http.uri.ext", "文件后缀", "URL 与路径", STRING),
    _f("http.uri.depth", "路径深度", "URL 与路径", NUMBER),
    _f("http.uri.query", "原始查询串", "URL 与路径", STRING),
    _f("http.query", "查询参数", "URL 与路径", STRING, requires_arg=True),
    _f("http.query.count", "查询参数个数", "URL 与路径", NUMBER),
    # method / headers / cookies / body
    _f("http.method", "请求方法", "HTTP 请求", ENUM),
    _f("http.header", "请求头", "HTTP 请求", STRING, requires_arg=True),
    _f("http.header.count", "请求头数量", "HTTP 请求", NUMBER),
    _f("http.ua", "User-Agent", "HTTP 请求", STRING),
    _f("http.referer", "Referer", "HTTP 请求", STRING),
    _f("http.content_type", "Content-Type", "HTTP 请求", STRING),
    _f("http.content_length", "Content-Length", "HTTP 请求", NUMBER),
    _f("http.accept", "Accept", "HTTP 请求", STRING),
    _f("http.accept_language", "Accept-Language", "HTTP 请求", STRING),
    _f("http.accept_encoding", "Accept-Encoding", "HTTP 请求", STRING),
    _f("http.origin", "Origin", "HTTP 请求", STRING),
    _f("http.xff", "X-Forwarded-For", "HTTP 请求", STRING),
    _f("http.range", "Range", "HTTP 请求", STRING),
    _f("http.has_auth", "是否带 Authorization", "HTTP 请求", BOOL),
    # cookies
    _f("http.cookie", "Cookie 参数", "HTTP 请求", STRING, requires_arg=True),
    _f("http.cookie_raw", "原始 Cookie", "HTTP 请求", STRING),
    _f("http.cookie.count", "Cookie 个数", "HTTP 请求", NUMBER),
    # body
    _f("http.body.raw", "原始请求体", "HTTP 请求", STRING),
    _f("http.body.size", "请求体大小", "HTTP 请求", NUMBER),
    _f("http.body.form", "表单参数", "HTTP 请求", STRING, requires_arg=True),
    _f("http.body.json", "JSON 字段", "HTTP 请求", STRING, requires_arg=True),
    _f("http.upload.filename", "上传文件名", "HTTP 请求", STRING),
    _f("http.upload.ext", "上传文件后缀", "HTTP 请求", STRING),
    # tls
    _f("tls.version", "TLS 版本", "客户端识别", STRING),
    _f("tls.cipher", "TLS 加密套件", "客户端识别", STRING),
    _f("tls.sni", "SNI", "客户端识别", STRING),
    _f("tls.ja3", "JA3 指纹", "客户端识别", STRING),
    # derived
    _f("derived.args_count", "参数总数", "时间与流量", NUMBER),
    _f("derived.time.hour", "当前小时", "时间与流量", NUMBER),
    _f("derived.time.weekday", "星期几", "时间与流量", NUMBER),
    _f("derived.fingerprint", "请求指纹", "时间与流量", STRING),
    # bot identification
    _f("bot.name", "Bot 名称", "客户端识别", STRING),
    _f("bot.category", "Bot 分类", "客户端识别", ENUM, extra_ops=["not_in"]),
    _f("bot.is_known", "匹配自建Bot库", "客户端识别", BOOL),
    # ua parsing (aligned with log stats: ua_family / ua_os)
    _f("ua.family", "UA 类型", "客户端识别", ENUM),
    _f("ua.os", "操作系统", "客户端识别", STRING),
    # traffic intelligence
    {
        "key": "traffic.global",
        "label": "全站请求量",
        "category": "时间与流量",
        **_TRAFFIC_FIELD_DEF,
    },
    {
        "key": "traffic.site",
        "label": "命中站点请求量",
        "category": "时间与流量",
        **_TRAFFIC_FIELD_DEF,
    },
    {
        "key": "traffic.origin_global",
        "label": "全站回源请求量",
        "category": "时间与流量",
        **_ORIGIN_TRAFFIC_FIELD_DEF,
    },
    {
        "key": "traffic.origin_site",
        "label": "命中站点回源请求量",
        "category": "时间与流量",
        **_ORIGIN_TRAFFIC_FIELD_DEF,
    },
    {
        "key": "system.cpu",
        "label": "系统CPU负载",
        "category": "时间与流量",
        **_SYSTEM_CPU_FIELD_DEF,
    },
]


def options_for_field(field: dict) -> list[dict[str, str]] | None:
    if field["value_type"] == BOOL:
        return BOOL_OPTIONS
    if field["value_type"] in (ENUM, TRAFFIC, SYSTEM):
        return FIELD_OPTIONS.get(field["key"])
    # Optional hint options for string fields (e.g. geo.isp) — UI may still allow free text
    return FIELD_OPTIONS.get(field["key"])


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
    ordered: list[dict] = []
    seen: set[str] = set()
    for name in CATEGORY_ORDER:
        if name in categories:
            ordered.append({"name": name, "fields": categories[name]})
            seen.add(name)
    for name, fields in categories.items():
        if name not in seen:
            ordered.append({"name": name, "fields": fields})
    return {
        "categories": ordered,
        "operators": OPERATORS,
        "operators_by_type": OPERATORS_BY_TYPE,
    }


def catalog_compact_for_llm() -> dict:
    """Lightweight field catalog for LLM prompts (no UI option lists)."""
    return {
        "condition_format": {
            "group": {"logic": "and|or", "conditions": ["<node>", "..."]},
            "leaf": {"field": "<key>", "op": "<operator>", "value": "<value>", "arg": "<optional>"},
            "notes": [
                "必须使用 logic + conditions，不要使用 all/any",
                "单条叶子条件可省略外层分组，系统会自动包裹",
                "requires_arg=true 的字段必须提供 arg（如 http.header 的 Header 名）",
                "field 必须严格使用 fields 列表中的 key，禁止自造字段名",
                "流量只能用 traffic.global / traffic.site / traffic.origin_global / traffic.origin_site；系统 CPU 用 system.cpu；CC/频率限制用 create_rate_limit",
            ],
        },
        "operator_selection": {
            "rule": "每个 field 只能使用该字段 operators 列表中的操作符，禁止混用其他 value_type 的写法",
            "by_value_type": OPERATORS_BY_TYPE,
            "canonical_examples": {
                "enum": {
                    "use": ["eq", "neq", "in_list"],
                    "avoid": ["equals", "not_equals", "contains", "regex"],
                    "fields": ["geo.country", "http.method", "net.scheme", "ua.family"],
                    "example": {
                        "field": "geo.country",
                        "op": "neq",
                        "value": "CN",
                        "meaning": "国家不等于 CN（禁止海外访问常用写法）",
                    },
                },
                "string": {
                    "use": [
                        "equals", "not_equals", "contains", "not_contains",
                        "starts_with", "ends_with", "regex", "in_list", "not_in",
                        "is_empty", "exists", "len_gt", "len_lt",
                    ],
                    "note": "字符串相等用 equals/not_equals，不要写 eq/neq",
                },
                "number": {
                    "use": ["eq", "neq", "gt", "gte", "lt", "lte", "between"],
                },
                "ip": {
                    "use": ["eq", "in_cidr", "in_list", "in_ip_group", "not_in_ip_group", "geo_in", "exists"],
                },
                "bool": {"use": ["eq"], "values": ["true", "false"]},
                "traffic": {
                    "use": ["compare"],
                    "fields": [
                        "traffic.global",
                        "traffic.site",
                        "traffic.origin_global",
                        "traffic.origin_site",
                    ],
                },
                "system": {
                    "use": ["compare"],
                    "fields": ["system.cpu"],
                },
            },
            "aliases_accepted_but_prefer_canonical": {
                "equals↔eq": "会按字段类型归一化，但仍应优先写该字段 operators 中的正式名",
                "not_equals↔neq": "geo.country 等 enum 应写 neq，不要写 not_equals",
            },
        },
        "traffic_value": {
            "field": "traffic.global | traffic.site | traffic.origin_global | traffic.origin_site",
            "op": "compare",
            "invalid_field_examples": [
                "traffic.global.request_count",
                "traffic.global.qps",
                "traffic.site.request_count",
                "traffic.origin_global.request_count",
            ],
            "value": {
                "window_sec": list(TRAFFIC_WINDOWS_SEC),
                "compare": [m["value"] for m in TRAFFIC_COMPARE_MODES],
                "threshold": "非负数（abs_gt/abs_lt/qps_gt/qps_lt 时必填）",
                "percent": "非负数（baseline_gt/baseline_lt 时必填，表示相对基线的百分比）",
            },
            "baseline_min_window_sec": TRAFFIC_BASELINE_MIN_WINDOW_SEC,
            "notes": [
                "禁止写 traffic.global.request_count 等带点后缀的字段",
                "baseline_gt/baseline_lt 要求 window_sec >= 300（5 分钟或更长）",
                "CC/频率限制应使用 create_rate_limit，不要用 traffic 字段模拟限速",
            ],
            "examples": [
                {
                    "description": "全站 5 分钟请求量超过 1000",
                    "leaf": {
                        "field": "traffic.global",
                        "op": "compare",
                        "value": {"window_sec": 300, "compare": "abs_gt", "threshold": 1000},
                    },
                },
                {
                    "description": "当前站点 QPS 超过 50",
                    "leaf": {
                        "field": "traffic.site",
                        "op": "compare",
                        "value": {"window_sec": 60, "compare": "qps_gt", "threshold": 50},
                    },
                },
                {
                    "description": "全站流量高于基线 200%",
                    "leaf": {
                        "field": "traffic.global",
                        "op": "compare",
                        "value": {"window_sec": 300, "compare": "baseline_gt", "percent": 200},
                    },
                },
                {
                    "description": "全站 5 分钟回源请求量超过 500",
                    "leaf": {
                        "field": "traffic.origin_global",
                        "op": "compare",
                        "value": {"window_sec": 300, "compare": "abs_gt", "threshold": 500},
                    },
                },
            ],
        },
        "system_value": {
            "field": "system.cpu",
            "op": "compare",
            "value": {
                "window_sec": list(SYSTEM_METRIC_WINDOWS_SEC),
                "compare": [m["value"] for m in SYSTEM_CPU_COMPARE_MODES],
                "threshold": "非负数（CPU% 或 Load）",
            },
            "notes": [
                "window_sec 仅支持 60/300/1800（1/5/30 分钟窗口均值）",
                "container_cpu_* 使用容器 cgroup CPU%；host_cpu_* 使用宿主机 /proc/stat",
            ],
            "examples": [
                {
                    "description": "5 分钟平均容器 CPU 超过 80%",
                    "leaf": {
                        "field": "system.cpu",
                        "op": "compare",
                        "value": {
                            "window_sec": 300,
                            "compare": "container_cpu_gt",
                            "threshold": 80,
                        },
                    },
                },
                {
                    "description": "1 分钟平均宿主机 CPU 超过 85%",
                    "leaf": {
                        "field": "system.cpu",
                        "op": "compare",
                        "value": {
                            "window_sec": 60,
                            "compare": "host_cpu_gt",
                            "threshold": 85,
                        },
                    },
                },
            ],
        },
        "block_page": {
            "custom_block_page_enabled": "bool，启用自定义拦截页",
            "block_page_status_code": "403|429|451|503",
            "block_page_html": "HTML，可用变量 request_id/client_ip/domain/method/uri/rule_id/rule_name/source",
        },
        "fields": [
            {
                "key": f["key"],
                "label": f["label"],
                "category": f["category"],
                "value_type": f["value_type"],
                "requires_arg": f.get("requires_arg", False),
                "operators": f.get("operators")
                or OPERATORS_BY_TYPE.get(f["value_type"], []),
                **(
                    {"compare_modes": [m["value"] for m in f["compare_modes"]]}
                    if f.get("compare_modes")
                    else {}
                ),
            }
            for f in FIELDS
        ],
        "operators_by_type": OPERATORS_BY_TYPE,
    }
