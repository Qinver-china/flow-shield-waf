"""Build knowledge context snapshots for LLM."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.fields.catalog import catalog_compact_for_llm
from app.models import RateLimit, Rule, Site
from app.models.rule import MODES
from app.schemas.ip_list import IpListCreate
from app.schemas.rate_limit import RateLimitCreate
from app.schemas.rule import RuleCreate
from app.schemas.site import SiteCreate

_STATIC_EXTENSIONS = [
    "css", "js", "mjs", "map",
    "jpg", "jpeg", "png", "gif", "webp", "svg", "ico", "avif", "bmp",
    "woff", "woff2", "ttf", "eot", "otf",
    "mp4", "webm", "mp3", "m4a", "ogg",
]

_DYNAMIC_EXTENSIONS = ["php", "php5", "phtml", "asp", "aspx", "jsp", "jspx", "cgi", "pl", "do", "action", "api"]


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

    return {
        "product": "流盾 WAF (Flow Shield WAF)",
        "field_catalog": catalog_compact_for_llm(),
        "modes": list(MODES),
        "policy_types": {
            "custom_rule": "按单次请求特征匹配（URI、Header、IP 等），不含频率统计",
            "rate_limit": "CC / 限速：在时间窗口内统计 keys 维度请求次数，超限后执行 mode",
            "whitelist": "白名单放行，list_type 固定 white",
        },
        "schemas": {
            "site": SiteCreate.model_json_schema(),
            "rule": RuleCreate.model_json_schema(),
            "rate_limit": RateLimitCreate.model_json_schema(),
            "whitelist": IpListCreate.model_json_schema(),
        },
        "tools_available": [
            "list_sites", "list_rules", "list_rate_limits",
            "query_logs", "get_log_stats",
            "create_site", "create_rule", "create_rate_limit", "create_whitelist_entry",
            "preview_rule", "preview_rate_limit",
        ],
        "sites": [
            {"id": s.id, "name": s.name, "domain": s.domain, "enabled": s.enabled}
            for s in sites
        ],
        "recent_rules": [
            {
                "id": r.id,
                "name": r.name,
                "mode": r.mode,
                "priority": r.priority,
                "site_ids": r.site_ids,
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
            }
            for rl in rate_limits
        ],
        "examples": {
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
            "cc_exclude_static": {
                "description": "CC 限速：仅静态资源（与动态页分开设阈值）",
                "tool": "create_rate_limit",
                "payload": {
                    "name": "CC - 静态资源",
                    "keys": [{"field": "ip.src"}],
                    "window": 60,
                    "threshold": 400,
                    "mode": "block",
                    "conditions": {
                        "logic": "or",
                        "conditions": [
                            {"field": "http.uri.ext", "op": "in_list", "value": _STATIC_EXTENSIONS},
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
        },
        "hints": [
            "conditions 为 {logic, conditions[]} 树结构，字段与操作符见 field_catalog",
            "site_ids 为空或省略表示全站策略",
            "CC / 频率限制必须用 create_rate_limit，不要用 create_rule",
            "分析攻击时先调用 get_log_stats，再按需 query_logs 查看样本",
            "写操作（create_*）会进入待确认，用户批准后才会落库",
        ],
    }
