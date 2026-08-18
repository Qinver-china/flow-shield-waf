"""Log query helpers for AI Guard tools (ClickHouse / LogQuery)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from app.schemas.log import LogQuery
from app.services.logging.query_clickhouse import STATS_DIMENSIONS

LOG_FILTER_OPS = ("eq", "ne", "contains", "not_contains", "like")

LOG_SCALAR_FIELDS: dict[str, str] = {
    "log_type": "日志类型：protection / access-control / audit",
    "source": "命中来源：rule / ratelimit / blacklist / whitelist / bot",
    "site_id": "站点 ID（整数）",
    "client_ip": "客户端 IP，精确匹配",
    "tcp_ip": "直连 IP（TCP 连接地址），精确匹配",
    "rule_id": "规则 ID（整数）",
    "rule_name": "规则名称，子串匹配",
    "action": "动作",
    "mode": "防护方式：observe / block / captcha / js_challenge / slide_captcha",
    "blocked": "是否拦截（true/false）",
    "domain": "访问域名",
    "geo_country": "国家代码，如 CN / US",
    "geo_region": "省/州",
    "geo_city": "城市",
    "geo_isp": "运营商",
    "geo_asn": "ASN（整数）",
    "method": "HTTP 方法：GET / POST 等",
    "scheme": "协议：http / https",
    "http_version": "HTTP 版本",
    "uri_path": "URI 路径",
    "request_uri": "原始请求行（路径+?查询串）",
    "uri_query": "原始查询串（? 后整段）",
    "uri_ext": "URI 扩展名，如 php / js",
    "referer_host": "Referer 主机",
    "cookie_name": "Cookie 参数名（存在该 Cookie 键）",
    "cookie": "Cookie 参数值（需配合 arg 指定参数名）",
    "cookie_count_bucket": "Cookie 个数分段：0 / 1-5 / 6-20 / 20+",
    "ip_is_private": "是否内网 IP（true/false）",
    "xff_first": "X-Forwarded-For 第一个 IP",
    "ua": "User-Agent 子串",
    "ua_family": "UA 家族",
    "ua_os": "操作系统",
    "ua_browser": "浏览器",
    "bot_name": "Bot 名称",
    "bot_category": "Bot 分类",
    "tls_version": "TLS 版本",
    "keyword": "在 URI / UA / 域名 / 完整 URL 中搜索关键词",
}

LOG_FILTER_FIELDS = frozenset(LOG_SCALAR_FIELDS)


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _parse_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_filters(raw: Any) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        return text or None
    if isinstance(raw, list):
        cleaned: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            field = item.get("field")
            op = item.get("op")
            value = item.get("value")
            if field not in LOG_FILTER_FIELDS or op not in LOG_FILTER_OPS:
                continue
            if value is None:
                continue
            cleaned.append({"field": field, "op": op, "value": value})
        return json.dumps(cleaned, ensure_ascii=False) if cleaned else None
    return None


def build_log_query_from_tool_args(arguments: dict[str, Any]) -> LogQuery:
    """Map AI tool arguments to LogQuery used by ClickHouse."""
    args = dict(arguments or {})
    hours = _parse_int(args.get("hours"))
    start = _parse_dt(args.get("start"))
    end = _parse_dt(args.get("end"))

    if start is None and end is None:
        end = datetime.utcnow()
        window_hours = min(max(hours or 24, 1), 168)
        start = end - timedelta(hours=window_hours)
    elif start is None:
        start = (end or datetime.utcnow()) - timedelta(hours=min(max(hours or 24, 1), 168))
    elif end is None:
        end = datetime.utcnow()

    page = max(1, _parse_int(args.get("page")) or 1)
    page_size = min(max(1, _parse_int(args.get("limit") or args.get("page_size")) or 50), 100)

    filters_list: list[dict[str, Any]] = []
    raw_filters = args.get("filters")
    if isinstance(raw_filters, list):
        filters_list.extend(raw_filters)
    elif isinstance(raw_filters, str) and raw_filters.strip():
        try:
            parsed = json.loads(raw_filters)
            if isinstance(parsed, list):
                filters_list.extend(parsed)
        except json.JSONDecodeError:
            pass
    filters_json = _normalize_filters(filters_list)

    return LogQuery(
        start=start,
        end=end,
        log_type=args.get("log_type"),
        source=args.get("source"),
        site_id=_parse_int(args.get("site_id")),
        client_ip=args.get("client_ip") or None,
        tcp_ip=args.get("tcp_ip") or None,
        rule_id=_parse_int(args.get("rule_id")),
        rule_name=args.get("rule_name") or None,
        action=args.get("action") or None,
        mode=args.get("mode") or None,
        blocked=_parse_bool(args.get("blocked")),
        domain=args.get("domain") or None,
        geo_country=args.get("geo_country") or None,
        geo_region=args.get("geo_region") or None,
        geo_city=args.get("geo_city") or None,
        geo_isp=args.get("geo_isp") or None,
        geo_asn=_parse_int(args.get("geo_asn")),
        method=args.get("method") or None,
        scheme=args.get("scheme") or None,
        http_version=args.get("http_version") or None,
        uri_path=args.get("uri_path") or None,
        request_uri=args.get("request_uri") or None,
        uri_query=args.get("uri_query") or None,
        uri_ext=args.get("uri_ext") or None,
        referer_host=args.get("referer_host") or None,
        ip_is_private=_parse_bool(args.get("ip_is_private")),
        xff_first=args.get("xff_first") or None,
        ua=args.get("ua") or None,
        ua_family=args.get("ua_family") or None,
        ua_os=args.get("ua_os") or None,
        ua_browser=args.get("ua_browser") or None,
        bot_name=args.get("bot_name") or None,
        bot_category=args.get("bot_category") or None,
        tls_version=args.get("tls_version") or None,
        keyword=args.get("keyword") or None,
        filters=filters_json,
        page=page,
        page_size=page_size,
    )


def log_query_catalog_for_llm() -> dict[str, Any]:
    """Compact reference for knowledge snapshot / prompts."""
    return {
        "storage": "ClickHouse 表 waf_logs",
        "tools": {
            "query_logs": "按筛选条件查询日志明细（支持分页）",
            "get_log_stats": "按相同筛选条件统计概览（总量、拦截、Top IP/规则/域名等）",
            "query_log_stats_group": "按维度聚合统计（如 client_ip、rule_id、domain）",
        },
        "time_window": {
            "hours": "回溯小时数，默认 24，最大 168",
            "start_end": "也可用 ISO8601 的 start / end 精确指定时间范围（最长 30 天）",
        },
        "filter_ops": list(LOG_FILTER_OPS),
        "scalar_fields": LOG_SCALAR_FIELDS,
        "filters_format": {
            "description": "filters 为条件数组，与日志页高级筛选一致；多个条件 AND 组合",
            "item": {"field": "<字段名>", "op": "<运算符>", "value": "<值或字符串数组>"},
            "example": [
                {"field": "blocked", "op": "eq", "value": "true"},
                {"field": "uri_path", "op": "contains", "value": "/admin"},
                {"field": "client_ip", "op": "eq", "value": ["1.2.3.4", "5.6.7.8"]},
            ],
        },
        "stats_dimensions": sorted(STATS_DIMENSIONS),
        "workflow": [
            "先根据用户问题确定时间范围与筛选字段",
            "需要明细样本时用 query_logs；需要总量/趋势/Top 排行用 get_log_stats",
            "需要按某一维度分组（如攻击 IP、命中规则）用 query_log_stats_group",
            "可组合 site_id、blocked、keyword 与 filters 数组做多条件筛选",
            "不要要求用户手动导出日志；自主调用工具查询",
        ],
        "examples": {
            "blocked_sql_injection_24h": {
                "tool": "query_logs",
                "arguments": {
                    "hours": 24,
                    "blocked": True,
                    "filters": [
                        {"field": "uri_path", "op": "contains", "value": "union"},
                    ],
                    "limit": 30,
                },
            },
            "top_attack_ips": {
                "tool": "query_log_stats_group",
                "arguments": {
                    "hours": 24,
                    "blocked": True,
                    "dimension": "client_ip",
                    "limit": 10,
                },
            },
            "site_overview": {
                "tool": "get_log_stats",
                "arguments": {"hours": 24, "site_id": 1},
            },
        },
    }
