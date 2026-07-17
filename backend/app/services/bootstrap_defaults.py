"""Built-in default WAF rules and rate limits seeded on first install.

Users may freely edit, disable, or delete these policies afterward.
Seeding is idempotent (tracked via Redis key).
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.fields import validate_condition
from app.models import RateLimit, Rule

log = logging.getLogger("waf.bootstrap.defaults")

SEED_KEY = "waf:bootstrap:default_policies_v1"
BUILTIN_PREFIX = "[内置] "

# Common static asset extensions (lowercase; engine normalizes uri.ext)
STATIC_EXTENSIONS = [
    "css", "js", "mjs", "map",
    "jpg", "jpeg", "png", "gif", "webp", "svg", "ico", "avif", "bmp",
    "woff", "woff2", "ttf", "eot", "otf",
    "mp4", "webm", "mp3", "m4a", "ogg",
    "m3u8", "ts",
]

DYNAMIC_EXTENSIONS = [
    "php", "php5", "phtml", "asp", "aspx", "jsp", "jspx", "cgi", "pl",
    "do", "action", "api",
]


def _leaf(
    field: str,
    op: str,
    *,
    value: Any = None,
    arg: str | None = None,
) -> dict:
    node: dict[str, Any] = {"field": field, "op": op}
    if arg is not None:
        node["arg"] = arg
    if value is not None:
        node["value"] = value
    return node


def _and(*conditions: dict) -> dict:
    return {"logic": "and", "conditions": list(conditions)}


def _or(*conditions: dict) -> dict:
    return {"logic": "or", "conditions": list(conditions)}


def _match_fields_regex(pattern: str, *fields: str) -> dict:
    return _or(*[_leaf(f, "regex", value=pattern) for f in fields])


def _static_file_condition() -> dict:
    return _or(_leaf("http.uri.ext", "in_list", value=STATIC_EXTENSIONS))


def _dynamic_page_condition() -> dict:
    """Dynamic HTML/API-style requests (non-static extension)."""
    return _or(
        _leaf("http.uri.ext", "in_list", value=DYNAMIC_EXTENSIONS),
        _leaf("http.uri.ext", "is_empty"),
    )


def _url_fields() -> tuple[str, ...]:
    return ("http.url", "http.uri.query", "http.body.raw", "http.request_uri")


# ---------------------------------------------------------------------------
# Custom rules
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[dict[str, Any]] = [
    # --- SQL injection ---
    {
        "name": f"{BUILTIN_PREFIX}SQL 注入 - UNION SELECT",
        "priority": 50,
        "mode": "observe",
        "conditions": _match_fields_regex(
            r"(?i)union\s+(all\s+)?select", *_url_fields()
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}SQL 注入 - 恒真条件",
        "priority": 51,
        "mode": "observe",
        "conditions": _match_fields_regex(
            r"(?i)(or|and)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?", *_url_fields()
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}SQL 注入 - 注释与延时函数",
        "priority": 52,
        "mode": "observe",
        "conditions": _or(
            _match_fields_regex(r"(?i)(/\*|--\s|#\s|;%00)", *_url_fields()),
            _match_fields_regex(
                r"(?i)(sleep\s*\(|benchmark\s*\(|pg_sleep\s*\(|waitfor\s+delay)",
                *_url_fields(),
            ),
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}SQL 注入 - 系统表探测",
        "priority": 53,
        "mode": "observe",
        "conditions": _match_fields_regex(
            r"(?i)(information_schema|sys\.(tables|columns)|mysql\.user|pg_catalog)",
            *_url_fields(),
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}SQL 注入 - 堆叠查询",
        "priority": 54,
        "mode": "observe",
        "conditions": _match_fields_regex(
            r"(?i);\s*(select|insert|update|delete|drop|alter|create)\s+",
            *_url_fields(),
        ),
    },
    # --- PHP attacks ---
    {
        "name": f"{BUILTIN_PREFIX}PHP 攻击 - phpinfo 探测",
        "priority": 60,
        "mode": "observe",
        "conditions": _or(
            _match_fields_regex(r"(?i)phpinfo\s*\(", *_url_fields()),
            _leaf("http.uri.path", "contains", value="phpinfo"),
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}PHP 攻击 - 远程文件包含",
        "priority": 61,
        "mode": "observe",
        "conditions": _match_fields_regex(
            r"(?i)(include|require)(_once)?\s*[\(\s]['\"]https?://",
            *_url_fields(),
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}PHP 攻击 - 代码执行函数",
        "priority": 62,
        "mode": "observe",
        "conditions": _match_fields_regex(
            r"(?i)\b(eval|assert|system|exec|shell_exec|passthru|proc_open)\s*\(",
            *_url_fields(),
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}PHP 攻击 - 敏感配置文件",
        "priority": 63,
        "mode": "observe",
        "conditions": _or(
            _leaf("http.uri.path", "regex", value=r"(?i)/(\.env|wp-config\.php|config\.php|\.git/)"),
            _match_fields_regex(r"(?i)(\.env|wp-config\.php|/\.git/)", "http.url", "http.request_uri"),
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}PHP 攻击 - 常见 WebShell",
        "priority": 64,
        "mode": "observe",
        "conditions": _match_fields_regex(
            r"(?i)(c99shell|r57shell|phpspy|b374k|eval-stdin\.php|cmd\.php)",
            *_url_fields(),
        ),
    },
    # --- Anti-PCDN ---
    {
        "name": f"{BUILTIN_PREFIX}反 PCDN - 机房 IP 拉取静态资源",
        "priority": 70,
        "mode": "observe",
        "conditions": _and(
            _leaf("geo.ip_type", "eq", value="hosting"),
            _static_file_condition(),
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}反 PCDN - HLS 分片高频拉流",
        "priority": 71,
        "mode": "observe",
        "conditions": _and(
            _or(
                _leaf("http.uri.ext", "in_list", value=["m3u8", "ts"]),
                _leaf("http.uri.path", "regex", value=r"(?i)\.(m3u8|ts)(\?|$)"),
            ),
            _leaf("geo.ip_type", "eq", value="hosting"),
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}反 PCDN - Range 分段滥用",
        "priority": 72,
        "mode": "observe",
        "conditions": _and(
            _leaf("http.range", "exists"),
            _or(
                _static_file_condition(),
                _leaf("http.uri.ext", "in_list", value=["mp4", "webm", "m3u8", "ts"]),
            ),
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}反 PCDN - 下载器/PCDN UA",
        "priority": 73,
        "mode": "observe",
        "conditions": _leaf(
            "http.ua",
            "regex",
            value=r"(?i)(pcdn|xunlei|thunder|qvod|duanju|aria2|wget|curl/|httpclient)",
        ),
    },
    {
        "name": f"{BUILTIN_PREFIX}反 PCDN - 无 Referer 批量图片",
        "priority": 74,
        "mode": "observe",
        "conditions": _and(
            _leaf("http.referer", "is_empty"),
            _leaf("http.uri.ext", "in_list", value=["jpg", "jpeg", "png", "gif", "webp"]),
            _leaf("http.method", "eq", value="GET"),
        ),
    },
]

# ---------------------------------------------------------------------------
# Rate limits
# ---------------------------------------------------------------------------

DEFAULT_RATE_LIMITS: list[dict[str, Any]] = [
    {
        "name": f"{BUILTIN_PREFIX}CC 防护 - 静态资源",
        "priority": 50,
        "keys": [{"field": "ip.src"}],
        "window": 60,
        "threshold": 400,
        "mode": "observe",
        "conditions": _static_file_condition(),
        "remark": "针对 CSS/JS/图片等静态文件，单 IP 每分钟请求上限较高",
    },
    {
        "name": f"{BUILTIN_PREFIX}CC 防护 - 动态页面",
        "priority": 51,
        "keys": [{"field": "ip.src"}],
        "window": 60,
        "threshold": 120,
        "mode": "observe",
        "conditions": _and(
            _dynamic_page_condition(),
            _leaf("http.method", "eq", value="GET"),
        ),
        "remark": "PHP/无后缀等动态页面 GET，阈值低于静态资源",
    },
    {
        "name": f"{BUILTIN_PREFIX}CC 防护 - 表单与登录 POST",
        "priority": 52,
        "keys": [{"field": "ip.src"}],
        "window": 300,
        "threshold": 60,
        "mode": "observe",
        "conditions": _and(
            _leaf("http.method", "eq", value="POST"),
            _or(
                _leaf("http.uri.path", "regex", value=r"(?i)/(login|signin|auth|register|wp-login)"),
                _leaf("http.content_type", "contains", value="application/x-www-form-urlencoded"),
            ),
        ),
        "remark": "登录/注册等表单提交，5 分钟窗口防爆破",
    },
    {
        "name": f"{BUILTIN_PREFIX}CC 防护 - API JSON 接口",
        "priority": 53,
        "keys": [{"field": "ip.src"}],
        "window": 60,
        "threshold": 80,
        "mode": "observe",
        "conditions": _and(
            _or(
                _leaf("http.method", "eq", value="POST"),
                _leaf("http.method", "eq", value="PUT"),
                _leaf("http.method", "eq", value="PATCH"),
            ),
            _or(
                _leaf("http.content_type", "contains", value="application/json"),
                _leaf("http.uri.path", "regex", value=r"(?i)/api(/|$)"),
            ),
        ),
        "remark": "REST/JSON API 写请求限速",
    },
    {
        "name": f"{BUILTIN_PREFIX}CC 防护 - API 读接口",
        "priority": 54,
        "keys": [{"field": "ip.src"}],
        "window": 60,
        "threshold": 150,
        "mode": "observe",
        "conditions": _and(
            _leaf("http.method", "eq", value="GET"),
            _leaf("http.uri.path", "regex", value=r"(?i)/api(/|$)"),
        ),
        "remark": "API GET 读请求单独限速",
    },
    {
        "name": f"{BUILTIN_PREFIX}CC 防护 - 静态资源单 URI",
        "priority": 55,
        "keys": [{"field": "ip.src"}, {"field": "http.uri.path"}],
        "window": 60,
        "threshold": 80,
        "mode": "observe",
        "conditions": _static_file_condition(),
        "remark": "同一 IP 对同一路径静态资源高频刷新（刷 CDN/PCDN 常见）",
    },
    {
        "name": f"{BUILTIN_PREFIX}CC 防护 - 机房 IP 动态页",
        "priority": 56,
        "keys": [{"field": "ip.src"}],
        "window": 60,
        "threshold": 60,
        "mode": "observe",
        "conditions": _and(
            _leaf("geo.ip_type", "eq", value="hosting"),
            _dynamic_page_condition(),
        ),
        "remark": "数据中心 IP 访问动态页面更严格限速",
    },
    {
        "name": f"{BUILTIN_PREFIX}CC 防护 - 全站兜底",
        "priority": 99,
        "keys": [{"field": "ip.src"}],
        "window": 60,
        "threshold": 600,
        "mode": "observe",
        "conditions": None,
        "remark": "全站单 IP 每分钟总请求观察阈值，建议结合上方细分策略",
    },
]


def _normalize_conditions(raw: dict | None) -> dict:
    if raw is None or raw == {}:
        return {"logic": "and", "conditions": []}
    return validate_condition(raw)


def _validate_catalog() -> None:
    """Fail fast at import if any built-in condition is invalid."""
    for spec in DEFAULT_RULES:
        _normalize_conditions(spec["conditions"])
    for spec in DEFAULT_RATE_LIMITS:
        if spec.get("conditions"):
            _normalize_conditions(spec["conditions"])


_validate_catalog()


async def seed_default_policies(db: AsyncSession) -> int:
    """Insert built-in rules/rate limits once. Returns number of rows created."""
    redis = get_redis()
    if await redis.get(SEED_KEY):
        return 0

    existing_rules = (
        await db.execute(select(func.count(Rule.id)).where(Rule.name.like(f"{BUILTIN_PREFIX}%")))
    ).scalar_one()
    if existing_rules:
        await redis.set(SEED_KEY, "1")
        log.info("builtin defaults already present (%d rules), marking seeded", existing_rules)
        return 0

    created = 0
    for spec in DEFAULT_RULES:
        db.add(
            Rule(
                name=spec["name"],
                site_ids=None,
                priority=int(spec.get("priority", 100)),
                mode=spec.get("mode", "block"),
                enabled=spec.get("enabled", True),
                conditions=_normalize_conditions(spec["conditions"]),
            )
        )
        created += 1

    for spec in DEFAULT_RATE_LIMITS:
        conditions = spec.get("conditions")
        db.add(
            RateLimit(
                name=spec["name"],
                site_ids=None,
                priority=int(spec.get("priority", 100)),
                enabled=spec.get("enabled", True),
                keys=spec.get("keys") or [{"field": "ip.src"}],
                window=int(spec.get("window", 60)),
                threshold=int(spec.get("threshold", 100)),
                mode=spec.get("mode", "block"),
                conditions=_normalize_conditions(conditions) if conditions else None,
                remark=spec.get("remark"),
            )
        )
        created += 1

    await db.commit()
    await redis.set(SEED_KEY, "1")
    log.info("seeded %d builtin policies (%d rules, %d ratelimits)",
             created, len(DEFAULT_RULES), len(DEFAULT_RATE_LIMITS))
    return created


async def ensure_default_policies(db: AsyncSession) -> int:
    """Called from application bootstrap."""
    try:
        return await seed_default_policies(db)
    except Exception:  # noqa: BLE001
        log.exception("seed default policies failed")
        return 0
