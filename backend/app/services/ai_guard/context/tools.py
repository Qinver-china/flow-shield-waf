"""OpenAI function tool definitions for chat."""
from __future__ import annotations

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
            "description": "查询最近 WAF 访问/拦截日志（ClickHouse），用于分析攻击或排查问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "回溯小时数，默认 24",
                        "default": 24,
                    },
                    "site_id": {"type": "integer", "description": "按站点过滤，可选"},
                    "blocked": {
                        "type": "boolean",
                        "description": "true=仅拦截，false=仅放行，省略=全部",
                    },
                    "client_ip": {"type": "string", "description": "按客户端 IP 过滤"},
                    "keyword": {
                        "type": "string",
                        "description": "在 URI/UA/域名中搜索关键词",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回条数上限，默认 50，最大 100",
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
            "description": "获取指定时间窗口内的日志统计概览（总量、拦截数、Top IP、Top 规则等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "统计窗口小时数，默认 24",
                        "default": 24,
                    },
                    "site_id": {"type": "integer", "description": "按站点过滤，可选"},
                },
                "required": [],
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
            "description": "创建自定义防护规则（基于请求特征匹配，不含频率限速；需用户确认后才会写入）",
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
                    "conditions": {"type": "object"},
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
                        "type": "object",
                        "description": "可选前置条件，如仅对动态页面限速、排除静态资源",
                    },
                    "remark": {"type": "string"},
                },
                "required": ["name", "window", "threshold", "mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_whitelist_entry",
            "description": "创建白名单条目（需用户确认后才会写入）",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "site_ids": {"type": "array", "items": {"type": "integer"}},
                    "conditions": {"type": "object"},
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
                    "conditions": {"type": "object"},
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
                    "conditions": {"type": "object"},
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
    "create_whitelist_entry",
})
