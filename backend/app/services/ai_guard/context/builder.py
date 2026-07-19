"""Build knowledge context snapshots for LLM."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.response_pages import ALLOWED_BLOCK_STATUS_CODES
from app.fields.catalog import catalog_compact_for_llm
from app.models import RateLimit, Rule, Site
from app.models.rule import MODES
from app.services.ai_guard.log_query import log_query_catalog_for_llm
from app.services.bot_catalog import category_options
from app.services.site_domains import site_domain_list

_STATIC_EXTENSIONS = [
    "css", "js", "mjs", "map",
    "jpg", "jpeg", "png", "gif", "webp", "svg", "ico", "avif", "bmp",
    "woff", "woff2", "ttf", "eot", "otf",
    "mp4", "webm", "mp3", "m4a", "ogg",
]

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
            "custom_rule": "按单次请求特征匹配（URI、Header、Body、Bot、流量等），不含频率统计",
            "rate_limit": "CC / 限速：在时间窗口内统计 keys 维度请求次数，超限后执行 mode",
            "whitelist": "白名单放行，list_type 固定 white",
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
            "whitelist": {
                "required": ["name", "conditions"],
                "optional": [
                    "site_ids", "enabled", "remark",
                    "custom_block_page_enabled", "block_page_status_code", "block_page_html",
                ],
            },
        },
        "tools_available": [
            "list_sites", "list_rules", "list_rate_limits",
            "query_logs", "get_log_stats", "query_log_stats_group",
            "create_site", "create_rule", "create_rate_limit", "create_whitelist_entry",
            "preview_rule", "preview_rate_limit",
        ],
        "log_query": log_query_catalog_for_llm(),
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
        "examples": {
            "xss_observe_script_tag": {
                "description": "XSS 观察规则：查询串含 script 标签（高置信度特征）",
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
                "description": "拦截未知 Bot（已知搜索引擎等除外）",
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
                "description": "全站请求量突增观察（5 分钟窗口）",
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
            "conditions 必须使用 {logic: and|or, conditions: [...]} 树结构，不要用 all/any",
            "单字段匹配写叶子节点 {field, op, value[, arg]}；多条件用 logic 分组",
            "site_ids 为空或省略表示全站策略；知识上下文中已有 sites 列表时无需再 list_sites",
            "CC / 频率限制必须用 create_rate_limit；traffic.global/site 仅用于特征规则，不是 CC",
            "写操作（create_*）会进入待确认，用户批准后才会落库；先用 preview_rule 校验",
            "防 XSS/SQLi 等建议先 mode=observe，确认无误报后再 block",
            "自定义拦截页：custom_block_page_enabled=true 时可设 block_page_status_code 与 block_page_html",
            "查日志：用 query_logs / get_log_stats / query_log_stats_group；筛选字段见 log_query",
        ],
    }
