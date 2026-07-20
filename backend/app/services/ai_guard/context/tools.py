"""OpenAI function tool definitions for chat."""
from __future__ import annotations

from app.services.ai_guard.log_query import LOG_FILTER_OPS, LOG_SCALAR_FIELDS
from app.services.logging.query_clickhouse import STATS_DIMENSIONS
_BLOCK_PAGE_PROPERTIES = {
    "custom_block_page_enabled": {
        "type": "boolean",
        "description": "是否启用自定义拦截页（命中规则/限速/白名单拦截时）",
    },
    "block_page_status_code": {
        "type": "integer",
        "description": "拦截页 HTTP 状态码，可选 403/429/451/503",
    },
    "block_page_html": {
        "type": "string",
        "description": "拦截页 HTML，支持变量 {request_id} {client_ip} {domain} {method} {uri} {rule_id} {rule_name} {source}",
    },
}

_CONDITION_SCHEMA = {
    "type": "object",
    "description": "条件树：{logic: and|or, conditions: [...]} 或叶子 {field, op, value[, arg]}",
}

_LOG_FILTER_ITEM = {
    "type": "object",
    "properties": {
        "field": {
            "type": "string",
            "enum": sorted(LOG_SCALAR_FIELDS),
            "description": "日志字段名",
        },
        "op": {
            "type": "string",
            "enum": list(LOG_FILTER_OPS),
            "description": "eq/ne/contains/not_contains/like",
        },
        "value": {
            "description": "筛选值；多值可用字符串数组（OR 组合）",
        },
    },
    "required": ["field", "op", "value"],
}

_LOG_TIME_PROPERTIES = {
    "hours": {
        "type": "integer",
        "description": "回溯小时数，默认 24，最大 168",
        "default": 24,
    },
    "start": {"type": "string", "description": "开始时间 ISO8601，可选"},
    "end": {"type": "string", "description": "结束时间 ISO8601，可选"},
}

_LOG_COMMON_FILTER_PROPERTIES = {
    "site_id": {"type": "integer", "description": "按站点 ID 过滤"},
    "blocked": {"type": "boolean", "description": "true=仅拦截，false=仅放行"},
    "client_ip": {"type": "string", "description": "客户端 IP"},
    "rule_id": {"type": "integer", "description": "规则 ID"},
    "rule_name": {"type": "string", "description": "规则名称子串"},
    "source": {
        "type": "string",
        "description": "命中来源：rule / ratelimit / blacklist / whitelist / bot",
    },
    "log_type": {
        "type": "string",
        "description": "protection / access-control / audit",
    },
    "mode": {"type": "string", "description": "observe / block / captcha 等"},
    "domain": {"type": "string"},
    "method": {"type": "string"},
    "uri_path": {"type": "string", "description": "URI 路径"},
    "request_uri": {"type": "string", "description": "原始请求行（路径+查询串）"},
    "uri_query": {"type": "string", "description": "原始查询串"},
    "uri_ext": {"type": "string", "description": "URI 扩展名"},
    "geo_country": {"type": "string", "description": "国家代码，如 CN"},
    "geo_city": {"type": "string"},
    "ua": {"type": "string", "description": "User-Agent 子串"},
    "ua_family": {"type": "string"},
    "bot_name": {"type": "string"},
    "bot_category": {"type": "string"},
    "tls_version": {"type": "string"},
    "keyword": {
        "type": "string",
        "description": "在 URI/UA/域名/完整 URL 中搜索关键词",
    },
    "filters": {
        "type": "array",
        "description": "高级筛选条件数组（与日志页一致）；多个条件 AND 组合，详见知识上下文 log_query",
        "items": _LOG_FILTER_ITEM,
    },
}

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_sites",
            "description": "列出所有站点",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_rules",
            "description": "列出自定义防护规则，可按 site_id 过滤",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_id": {"type": "integer", "description": "站点 ID，可选"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_rate_limits",
            "description": "列出 CC / 限速策略，可按 site_id 过滤",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_id": {"type": "integer", "description": "站点 ID，可选"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_logs",
            "description": (
                "查询 WAF 访问/拦截日志明细（ClickHouse）。"
                "请根据分析目标自主组合 site_id、blocked、keyword 与 filters 筛选；"
                "知识上下文 log_query 含完整字段与示例。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    **_LOG_TIME_PROPERTIES,
                    **_LOG_COMMON_FILTER_PROPERTIES,
                    "page": {"type": "integer", "description": "页码，默认 1", "default": 1},
                    "limit": {
                        "type": "integer",
                        "description": "每页条数，默认 50，最大 100",
                        "default": 50,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_log_stats",
            "description": (
                "获取日志统计概览（总量、拦截数、趋势、Top IP/规则/域名等）。"
                "筛选参数与 query_logs 相同，可先统计再按需 query_logs 拉明细。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    **_LOG_TIME_PROPERTIES,
                    **_LOG_COMMON_FILTER_PROPERTIES,
                    "trend_granularity": {
                        "type": "string",
                        "description": "趋势粒度：5m/10m/1h/1d 等，省略则自动",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_log_stats_group",
            "description": (
                "按维度聚合统计日志（如 client_ip、rule_id、domain、source）。"
                "用于找出攻击 IP、高频命中规则等；筛选参数与 query_logs 相同。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    **_LOG_TIME_PROPERTIES,
                    **_LOG_COMMON_FILTER_PROPERTIES,
                    "dimension": {
                        "type": "string",
                        "enum": sorted(STATS_DIMENSIONS),
                        "description": "聚合维度",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回分组数量上限，默认 20，最大 100",
                        "default": 20,
                    },
                },
                "required": ["dimension"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_site",
            "description": "创建站点（需用户确认后才会写入）",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                    "domain": {
                        "type": "string",
                        "description": "兼容旧参数，等价于 domains 仅含一个域名",
                    },
                    "origin_host": {"type": "string"},
                    "origin_protocol": {
                        "type": "string",
                        "enum": ["follow", "http", "https"],
                    },
                    "listen_http": {"type": "boolean"},
                    "listen_https": {"type": "boolean"},
                    "force_https": {"type": "boolean"},
                    "certificate_id": {"type": "integer"},
                    "enabled": {"type": "boolean"},
                },
                "required": ["name", "origin_host"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_rule",
            "description": (
                "创建自定义防护规则（URI/Header/Body/Bot/流量/TLS 等特征匹配，"
                "可选 observe/block/验证码；不含 CC 限速，也不是黑/白名单。"
                "用户要黑名单请用 create_blacklist_entry；要白名单用 create_whitelist_entry；"
                "要防护例外用 create_exception。需用户确认后才会写入）"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "mode": {
                        "type": "string",
                        "enum": ["observe", "block", "captcha", "js_challenge", "slide_captcha"],
                    },
                    "priority": {"type": "integer"},
                    "site_ids": {"type": "array", "items": {"type": "integer"}},
                    "enabled": {"type": "boolean"},
                    "conditions": _CONDITION_SCHEMA,
                    **_BLOCK_PAGE_PROPERTIES,
                },
                "required": ["name", "mode", "conditions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_rate_limit",
            "description": "创建 CC / 限速策略（按 IP 等维度统计时间窗口内请求次数；需用户确认后才会写入）",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "keys": {
                        "type": "array",
                        "description": "限速维度，默认按源 IP",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "arg": {"type": "string"},
                            },
                            "required": ["field"],
                        },
                    },
                    "window": {
                        "type": "integer",
                        "description": "时间窗口（秒），如 60 表示 1 分钟",
                    },
                    "threshold": {
                        "type": "integer",
                        "description": "窗口内允许的最大请求数",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["observe", "block", "captcha", "js_challenge", "slide_captcha"],
                    },
                    "priority": {"type": "integer"},
                    "site_ids": {"type": "array", "items": {"type": "integer"}},
                    "enabled": {"type": "boolean"},
                    "conditions": {
                        **_CONDITION_SCHEMA,
                        "description": "可选前置条件，如仅对动态页面限速、排除静态资源",
                    },
                    "remark": {"type": "string"},
                    **_BLOCK_PAGE_PROPERTIES,
                },
                "required": ["name", "window", "threshold", "mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_blacklist_entry",
            "description": (
                "创建黑名单条目（访问控制：命中即拒绝）。"
                "适用于禁止某 IP/国家/地区等访问；不要用 create_rule 代替。"
                "需用户确认后才会写入"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "site_ids": {"type": "array", "items": {"type": "integer"}},
                    "conditions": _CONDITION_SCHEMA,
                    "remark": {"type": "string"},
                    "enabled": {"type": "boolean"},
                    **_BLOCK_PAGE_PROPERTIES,
                },
                "required": ["name", "conditions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_whitelist_entry",
            "description": (
                "创建白名单条目（访问控制：命中放行）。"
                "不要与防护例外混淆；例外请用 create_exception。"
                "需用户确认后才会写入"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "site_ids": {"type": "array", "items": {"type": "integer"}},
                    "conditions": _CONDITION_SCHEMA,
                    "remark": {"type": "string"},
                    "enabled": {"type": "boolean"},
                    **_BLOCK_PAGE_PROPERTIES,
                },
                "required": ["name", "conditions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_exception",
            "description": (
                "创建防护例外（匹配请求跳过全部或指定防护）。"
                "scope=all 跳过全部防护；rules 仅跳过自定义规则；ratelimit 仅跳过限速。"
                "不要用白名单代替例外。需用户确认后才会写入"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "scope": {
                        "type": "string",
                        "enum": ["all", "rules", "ratelimit"],
                        "description": "例外范围，默认 all",
                    },
                    "site_ids": {"type": "array", "items": {"type": "integer"}},
                    "conditions": {
                        **_CONDITION_SCHEMA,
                        "description": "匹配条件；scope=all 时必填且不能为空",
                    },
                    "remark": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
                "required": ["name", "conditions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "preview_rule",
            "description": "校验自定义规则条件是否合法，不写入数据库",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "mode": {"type": "string"},
                    "conditions": _CONDITION_SCHEMA,
                },
                "required": ["conditions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "preview_rate_limit",
            "description": "校验 CC / 限速策略参数是否合法，不写入数据库",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "keys": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "arg": {"type": "string"},
                            },
                            "required": ["field"],
                        },
                    },
                    "window": {"type": "integer"},
                    "threshold": {"type": "integer"},
                    "mode": {"type": "string"},
                    "conditions": _CONDITION_SCHEMA,
                },
                "required": ["window", "threshold", "mode"],
            },
        },
    },
]

WRITE_TOOLS = frozenset({
    "create_site",
    "create_rule",
    "create_rate_limit",
    "create_blacklist_entry",
    "create_whitelist_entry",
    "create_exception",
})

DEFENSE_READ_TOOL_NAMES = frozenset({
    "query_logs",
    "get_log_stats",
    "query_log_stats_group",
    "list_rules",
})

_SUBMIT_ANALYSIS_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_analysis",
        "description": (
            "提交最终分析结论。分析完成后必须调用此工具。"
            "若判断无需新建防护规则，设 create_rule=false 并省略 suggested_rule。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "攻击或异常概述"},
                "attack_indicators": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "攻击/异常请求共性",
                },
                "benign_indicators": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "可能误报的正常流量特征",
                },
                "confidence": {
                    "type": "number",
                    "description": "置信度 0-1",
                },
                "create_rule": {
                    "type": "boolean",
                    "description": "是否建议创建防护规则；false 表示仅记录分析、不建规则",
                },
                "suggested_rule": {
                    "type": "object",
                    "description": "create_rule=true 时必填",
                    "properties": {
                        "name": {"type": "string"},
                        "mode": {
                            "type": "string",
                            "enum": ["observe", "block", "captcha", "js_challenge", "slide_captcha"],
                        },
                        "priority": {"type": "integer"},
                        "site_ids": {"type": "array", "items": {"type": "integer"}},
                        "enabled": {"type": "boolean"},
                        "conditions": _CONDITION_SCHEMA,
                    },
                    "required": ["name", "mode", "conditions"],
                },
                "evidence": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "request_id": {"type": "string"},
                            "note": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["summary", "confidence", "create_rule"],
        },
    },
}

DEFENSE_TOOL_DEFINITIONS: list[dict] = [
    tool
    for tool in TOOL_DEFINITIONS
    if tool.get("function", {}).get("name") in DEFENSE_READ_TOOL_NAMES
] + [_SUBMIT_ANALYSIS_TOOL]
