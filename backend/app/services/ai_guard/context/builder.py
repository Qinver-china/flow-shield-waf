"""Build knowledge context snapshots for LLM."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.response_pages import ALLOWED_BLOCK_STATUS_CODES
from app.fields.catalog import catalog_compact_for_llm
from app.models import RateLimit, Rule, Site
from app.models.ai_guard import APPLY_MODES
from app.models.rule import MODES
from app.services.ai_guard.defense.triggers import TRIGGER_TYPES
from app.services.ai_guard.log_query import log_query_catalog_for_llm
from app.services.bot_catalog import category_options
from app.services.site_domains import site_domain_list

_DYNAMIC_EXTENSIONS = ["php", "php5", "phtml", "asp", "aspx", "jsp", "jspx", "cgi", "pl", "do", "action", "api"]


def _rule_resource_fields() -> dict:
    return {
        "required": ["name", "mode", "conditions"],
        "optional": [
            "priority (默认 100)",
            "site_ids (空=全站)",
            "enabled (默认 true)",
            "custom_block_page_enabled",
            "block_page_status_code",
            "block_page_html",
        ],
        "modes": list(MODES),
        "block_page_status_codes": sorted(ALLOWED_BLOCK_STATUS_CODES),
    }


def _defense_knowledge() -> dict:
    return {
        "apply_modes": {
            "suggest_only": "仅生成建议规则，需面板或邮件链接手动应用",
            "auto_observe": "自动创建 observe 模式规则",
            "auto_block": "高置信度且拦截占比高时自动 block，否则 observe",
        },
        "apply_mode_values": list(APPLY_MODES),
        "trigger_types": [
            {
                "type": item["type"],
                "label": item["label"],
                "params": [
                    {
                        "key": spec["key"],
                        "label": spec.get("label") or spec["key"],
                        "required": bool(spec.get("required")),
                    }
                    for spec in item.get("params", [])
                ],
            }
            for item in TRIGGER_TYPES
        ],
        "rule_generation_notes": [
            "多轮分析：初始仅近 30 分钟放行日志；不足时用 query_logs 等工具扩大范围",
            "完成后调用 submit_analysis；create_rule=false 表示不建规则",
            "suggested_rule.conditions 必须使用 field_catalog 中的合法 key 与该字段 operators",
            "enum 字段（如 geo.country）用 eq/neq/in_list，不要用 equals/not_equals",
            "流量条件写 traffic.global/traffic.site/traffic.origin_global/traffic.origin_site + op=compare，禁止 traffic.global.request_count",
            "CC/频率攻击应建议 create_rate_limit，不要用 traffic 字段",
            "访问控制封禁（国家/IP）应建议 create_blacklist_entry，不要用 create_rule",
            "建议先 mode=observe，高置信度再 block",
        ],
    }


def knowledge_for_defense(field_catalog: dict | None = None) -> dict:
    """Compact field catalog slice for automated defense analysis prompts."""
    catalog = field_catalog or catalog_compact_for_llm()
    return {
        "condition_format": catalog.get("condition_format"),
        "operator_selection": catalog.get("operator_selection"),
        "traffic_value": catalog.get("traffic_value"),
        "system_value": catalog.get("system_value"),
        "fields": catalog.get("fields"),
        "operators_by_type": catalog.get("operators_by_type"),
    }


async def build_knowledge_snapshot(db: AsyncSession) -> dict:
    sites = (
        await db.execute(select(Site).order_by(Site.id.desc()).limit(50))
    ).scalars().all()
    rules = (
        await db.execute(select(Rule).order_by(Rule.priority.asc()).limit(30))
    ).scalars().all()
    rate_limits = (
        await db.execute(select(RateLimit).order_by(RateLimit.priority.asc(), RateLimit.id.asc()).limit(20))
    ).scalars().all()
    bot_categories = await category_options(db)

    field_catalog = catalog_compact_for_llm()
    if bot_categories:
        field_catalog = {
            **field_catalog,
            "bot_category_values": [opt["value"] for opt in bot_categories],
        }

    return {
        "product": "流盾 WAF (Flow Shield WAF)",
        "field_catalog": field_catalog,
        "modes": list(MODES),
        "policy_types": {
            "blacklist": {
                "tool": "create_blacklist_entry",
                "label": "黑名单",
                "when": "用户明确要黑名单/封禁访问/禁止某 IP、国家、地区等来源访问",
                "effect": "命中即拒绝访问（访问控制），不是自定义特征规则",
                "do_not_use": "create_rule",
            },
            "whitelist": {
                "tool": "create_whitelist_entry",
                "label": "白名单",
                "when": "用户要白名单/放行/信任某来源",
                "effect": "命中放行",
                "do_not_use": "create_exception（例外是跳过防护，不是放行语义）",
            },
            "exception": {
                "tool": "create_exception",
                "label": "防护例外",
                "when": "用户要防护例外/跳过 WAF/避免误拦（如编辑器、回调）",
                "effect": "匹配请求跳过全部或指定防护（scope=all|rules|ratelimit）",
                "do_not_use": "create_whitelist_entry",
            },
            "custom_rule": {
                "tool": "create_rule",
                "label": "自定义规则",
                "when": "用户要自定义规则/观察规则/按 URI·Header·Body·Bot·流量等特征匹配",
                "effect": "按条件匹配并执行 mode（observe/block/验证码等），不含频率统计",
                "do_not_use": "create_blacklist_entry（黑名单没有 observe；封禁访问控制用黑名单）",
            },
            "rate_limit": {
                "tool": "create_rate_limit",
                "label": "CC / 限速",
                "when": "用户要 CC、限速、频率限制",
                "effect": "时间窗口内按 keys 计数，超限执行 mode",
                "do_not_use": "create_rule + traffic 字段模拟限速",
            },
        },
        "resource_fields": {
            "rule": _rule_resource_fields(),
            "rate_limit": {
                "required": ["name", "window", "threshold", "mode"],
                "optional": [
                    "keys (默认 [{field: ip.src}])",
                    "priority", "site_ids", "enabled", "conditions", "remark",
                    "custom_block_page_enabled", "block_page_status_code", "block_page_html",
                ],
            },
            "blacklist": {
                "required": ["name", "conditions"],
                "optional": [
                    "site_ids", "enabled", "remark",
                    "custom_block_page_enabled", "block_page_status_code", "block_page_html",
                ],
            },
            "whitelist": {
                "required": ["name", "conditions"],
                "optional": [
                    "site_ids", "enabled", "remark",
                    "custom_block_page_enabled", "block_page_status_code", "block_page_html",
                ],
            },
            "exception": {
                "required": ["name", "conditions"],
                "optional": [
                    "scope (all|rules|ratelimit，默认 all)",
                    "site_ids", "enabled", "remark",
                ],
                "notes": [
                    "scope=all 时必须至少一条匹配条件",
                    "scope=rules 仅跳过自定义规则；scope=ratelimit 仅跳过限速",
                ],
            },
        },
        "tools_available": [
            "list_sites", "list_rules", "list_rate_limits",
            "query_logs", "get_log_stats", "query_log_stats_group",
            "create_site", "create_rule", "create_rate_limit",
            "create_blacklist_entry", "create_whitelist_entry", "create_exception",
            "preview_rule", "preview_rate_limit",
        ],
        "log_query": log_query_catalog_for_llm(),
        "defense": _defense_knowledge(),
        "examples": {
            "blacklist_block_overseas": {
                "description": "黑名单：禁止海外访问（国家不等于 CN）",
                "tool": "create_blacklist_entry",
                "payload": {
                    "name": "禁止海外访问",
                    "enabled": True,
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {"field": "geo.country", "op": "neq", "value": "CN"},
                        ],
                    },
                },
            },
            "whitelist_office_ip": {
                "description": "白名单：放行办公网段",
                "tool": "create_whitelist_entry",
                "payload": {
                    "name": "办公网放行",
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {"field": "ip.src", "op": "in_cidr", "value": "10.0.0.0/8"},
                        ],
                    },
                },
            },
            "exception_skip_rules_for_editor": {
                "description": "防护例外：后台编辑器跳过自定义规则，避免富文本误拦",
                "tool": "create_exception",
                "payload": {
                    "name": "后台编辑器例外",
                    "scope": "rules",
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {"field": "http.uri.path", "op": "starts_with", "value": "/wp-admin"},
                        ],
                    },
                },
            },
            "xss_observe_script_tag": {
                "description": "自定义规则：XSS 观察（查询串含 script 标签）",
                "tool": "create_rule",
                "payload": {
                    "name": "XSS-观察-script标签-查询串",
                    "mode": "observe",
                    "priority": 100,
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {"field": "http.method", "op": "in_list", "value": ["GET", "POST", "PUT", "PATCH"]},
                            {"field": "http.uri.query", "op": "regex", "value": "(?i)<\\s*script\\b[^>]*>"},
                        ],
                    },
                },
            },
            "bot_block_unknown": {
                "description": "自定义规则：拦截未知 Bot",
                "tool": "create_rule",
                "payload": {
                    "name": "拦截未知 Bot",
                    "mode": "block",
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {"field": "ua.family", "op": "eq", "value": "bot"},
                            {"field": "bot.is_known", "op": "eq", "value": "false"},
                        ],
                    },
                },
            },
            "traffic_spike": {
                "description": "自定义规则：全站请求量突增观察（5 分钟，高于基线 200%）",
                "tool": "create_rule",
                "payload": {
                    "name": "全站流量突增-观察",
                    "mode": "observe",
                    "conditions": {
                        "logic": "and",
                        "conditions": [
                            {
                                "field": "traffic.global",
                                "op": "compare",
                                "value": {
                                    "window_sec": 300,
                                    "compare": "baseline_gt",
                                    "percent": 200,
                                },
                            },
                        ],
                    },
                },
            },
            "cc_dynamic_pages": {
                "description": "CC 限速：仅动态页面，排除静态资源",
                "tool": "create_rate_limit",
                "payload": {
                    "name": "CC - 动态页面",
                    "keys": [{"field": "ip.src"}],
                    "window": 60,
                    "threshold": 120,
                    "mode": "block",
                    "site_ids": [],
                    "conditions": {
                        "logic": "or",
                        "conditions": [
                            {"field": "http.uri.ext", "op": "in_list", "value": _DYNAMIC_EXTENSIONS},
                            {"field": "http.uri.ext", "op": "is_empty"},
                        ],
                    },
                },
            },
            "custom_block_sql_injection": {
                "description": "自定义规则：拦截 URI 中疑似 SQL 注入",
                "tool": "create_rule",
                "payload": {
                    "name": "拦截 SQL 注入特征",
                    "mode": "block",
                    "priority": 100,
                    "conditions": {
                        "logic": "or",
                        "conditions": [
                            {"field": "http.uri.query", "op": "regex", "value": "(?i)(union\\s+select|sleep\\(|benchmark\\()"},
                        ],
                    },
                },
            },
            "analyze_blocked_logs": {
                "description": "分析最近 24 小时拦截日志中的攻击 IP",
                "tool": "query_log_stats_group",
                "payload": {
                    "hours": 24,
                    "blocked": True,
                    "dimension": "client_ip",
                    "limit": 10,
                },
            },
        },
        "hints": [
            "先根据用户意图在 policy_types 中选型，再调用对应工具；禁止用 create_rule 代替黑名单/白名单/例外",
            "conditions 必须使用 {logic: and|or, conditions: [...]}，不要用 all/any",
            "field 必须严格使用 field_catalog.fields 中的 key；op 必须在该字段 operators 内",
            "enum 字段（geo.country 等）用 eq/neq/in_list；禁止写 not_equals/equals/contains",
            "流量条件：field=traffic.global|traffic.site|traffic.origin_global|traffic.origin_site，op=compare；CC 必须用 create_rate_limit",
            "site_ids 为空或省略表示全站；写操作会进入待确认，用户批准后才落库",
            "防 XSS/SQLi 等自定义规则建议先 mode=observe",
            "查日志用 query_logs / get_log_stats / query_log_stats_group",
        ],
        "sites": [
            {
                "id": s.id,
                "name": s.name,
                "domain": s.domain,
                "domains": site_domain_list(s),
                "enabled": s.enabled,
            }
            for s in sites
        ],
        "recent_rules": [
            {
                "id": r.id,
                "name": r.name,
                "mode": r.mode,
                "priority": r.priority,
                "site_ids": r.site_ids,
                "enabled": r.enabled,
                "custom_block_page_enabled": r.custom_block_page_enabled,
            }
            for r in rules
        ],
        "recent_rate_limits": [
            {
                "id": rl.id,
                "name": rl.name,
                "priority": rl.priority,
                "window": rl.window,
                "threshold": rl.threshold,
                "mode": rl.mode,
                "site_ids": rl.site_ids,
                "enabled": rl.enabled,
            }
            for rl in rate_limits
        ],
    }
