"""ClickHouse-backed log queries and aggregations."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.clickhouse import get_clickhouse
from app.core.db import SessionLocal
from app.models import BotProfile, IpList, RateLimit, Rule
from app.models.site import Site
from app.schemas.log import LogQuery, LogStatsGroupItem, LogStatsGroupOut
from app.services.logging.labels import (
    format_dimension_label,
    format_rule_stats_label,
    set_bot_category_labels,
)
from app.services.bot_catalog import category_label_map

STATS_DIMENSIONS = frozenset({
    "rule_id", "client_ip", "source", "mode", "site_id", "domain", "geo_country",
    "method", "blocked", "log_type", "ip_is_private", "xff_first", "geo_region",
    "geo_city", "geo_isp", "geo_ip_type", "geo_asn", "scheme", "http_version",
    "uri_path", "uri_ext", "uri_depth", "uri_pattern", "full_url", "referer_host",
    "query_count_bucket", "ua", "ua_family", "ua_os", "ua_browser", "bot_name",
    "bot_category", "tls_version",
    "tls_ja3", "hour_of_day", "weekday",
})

_DIM_COLUMN = {
    "rule_id": "rule_id",
    "client_ip": "client_ip",
    "source": "source",
    "mode": "mode",
    "site_id": "site_id",
    "domain": "domain",
    "geo_country": "geo_country",
    "method": "method",
    "blocked": "blocked",
    "log_type": "log_type",
    "ip_is_private": "ip_is_private",
    "xff_first": "xff_first",
    "geo_region": "geo_region",
    "geo_city": "geo_city",
    "geo_isp": "geo_isp",
    "geo_ip_type": "geo_ip_type",
    "geo_asn": "geo_asn",
    "scheme": "scheme",
    "http_version": "http_version",
    "uri_path": "uri_path",
    "uri_ext": "uri_ext",
    "uri_depth": "uri_depth",
    "uri_pattern": "uri_pattern",
    "referer_host": "referer_host",
    "ua": "ua",
    "ua_family": "ua_family",
    "ua_os": "ua_os",
    "ua_browser": "ua_browser",
    "bot_name": "bot_name",
    "bot_category": "bot_category",
    "tls_version": "tls_version",
    "tls_ja3": "tls_ja3",
}


def _window(start: datetime | None, end: datetime | None, hours: int) -> tuple[datetime, datetime]:
    end_ts = end or datetime.utcnow()
    start_ts = start or (end_ts - timedelta(hours=hours))
    if end_ts - start_ts > timedelta(days=30):
        raise ValueError("查询时间范围不能超过 30 天")
    return start_ts, end_ts


async def _site_label_map(site_ids: list[int]) -> dict[int, tuple[str, str]]:
    """Resolve site id -> (name, domain) for stats labels."""
    ids = sorted({sid for sid in site_ids if sid is not None})
    if not ids:
        return {}
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(Site.id, Site.name, Site.domain).where(Site.id.in_(ids))
            )
        ).all()
    return {int(r[0]): (str(r[1]), str(r[2])) for r in rows}


def _rule_ref(source: str | None, rule_id: int) -> tuple[str, int]:
    return (source or "unknown", int(rule_id))


def _pick_rule_name(
    source: str | None,
    rule_id: int,
    snapshot: str | None,
    label_map: dict[tuple[str, int], str],
) -> str:
    """Prefer current DB name; fall back to log snapshot, then generic label."""
    return label_map.get(_rule_ref(source, rule_id)) or (snapshot or "").strip() or f"规则 #{rule_id}"


def _pick_site_display(
    site_id: int,
    domain_snapshot: str | None,
    label_map: dict[int, tuple[str, str]],
) -> tuple[str | None, str | None]:
    """Prefer current DB site name/domain; fall back to log snapshot domain."""
    name, db_domain = label_map.get(site_id, (None, None))
    domain = db_domain or (domain_snapshot or "").strip() or None
    return name, domain


async def _rule_label_map(
    refs: list[tuple[str, int]],
    *,
    snapshots: dict[tuple[str, int], str] | None = None,
) -> dict[tuple[str, int], str]:
    """Resolve (source, rule_id) -> current display name from the config tables."""
    snapshots = snapshots or {}
    unique_refs = sorted({_rule_ref(source, rid) for source, rid in refs})
    if not unique_refs:
        return {}

    by_source: dict[str, list[int]] = {}
    for source, rid in unique_refs:
        by_source.setdefault(source, []).append(rid)

    names: dict[tuple[str, int], str] = {}
    async with SessionLocal() as db:
        if ids := by_source.get("rule"):
            rows = (
                await db.execute(select(Rule.id, Rule.name).where(Rule.id.in_(ids)))
            ).all()
            for rid, name in rows:
                names[("rule", int(rid))] = str(name)
        if ids := by_source.get("ratelimit"):
            rows = (
                await db.execute(select(RateLimit.id, RateLimit.name).where(RateLimit.id.in_(ids)))
            ).all()
            for rid, name in rows:
                names[("ratelimit", int(rid))] = str(name)
        iplist_ids = sorted(
            set(by_source.get("blacklist", [])) | set(by_source.get("whitelist", []))
        )
        if iplist_ids:
            rows = (
                await db.execute(select(IpList.id, IpList.name).where(IpList.id.in_(iplist_ids)))
            ).all()
            id_to_name = {int(rid): str(name) for rid, name in rows}
            for src in ("blacklist", "whitelist"):
                for rid in by_source.get(src, []):
                    if rid in id_to_name:
                        names[(src, rid)] = id_to_name[rid]
        if ids := by_source.get("bot"):
            rows = (
                await db.execute(select(BotProfile.id, BotProfile.name).where(BotProfile.id.in_(ids)))
            ).all()
            for rid, name in rows:
                names[("bot", int(rid))] = str(name)

    return {
        key: names.get(key) or (snapshots.get(key) or "").strip() or f"规则 #{key[1]}"
        for key in unique_refs
    }


def _paginate(page: int, page_size: int) -> tuple[int, int, str]:
    page_size = min(max(1, page_size), 100)
    page = max(1, page)
    offset = (page - 1) * page_size
    return page, page_size, f"LIMIT {int(page_size)} OFFSET {int(offset)}"


def _dimension_groups_inner_sql(dimension: str, where: str) -> str:
    """SQL subquery that returns one row per distinct dimension group."""
    if dimension == "rule_id":
        return (
            f"SELECT rule_id, source FROM waf_logs WHERE {where} AND rule_id IS NOT NULL "
            f"GROUP BY rule_id, source"
        )
    if dimension == "site_id":
        return f"SELECT site_id FROM waf_logs WHERE {where} GROUP BY site_id"
    if dimension == "query_count_bucket":
        return (
            f"SELECT multiIf(query_count = 0, '0', query_count <= 5, '1-5', "
            f"query_count <= 20, '6-20', '20+') AS bucket "
            f"FROM waf_logs WHERE {where} GROUP BY bucket"
        )
    if dimension == "hour_of_day":
        return f"SELECT toHour(ts) AS h FROM waf_logs WHERE {where} GROUP BY h"
    if dimension == "weekday":
        return f"SELECT toDayOfWeek(ts) AS d FROM waf_logs WHERE {where} GROUP BY d"
    if dimension == "blocked":
        return f"SELECT blocked FROM waf_logs WHERE {where} GROUP BY blocked"
    if dimension == "full_url":
        return (
            f"SELECT concat(scheme, '://', domain, uri) AS full_url FROM waf_logs "
            f"WHERE {where} AND domain != '' AND uri != '' GROUP BY full_url"
        )
    col = _DIM_COLUMN.get(dimension, dimension)
    return f"SELECT {col} FROM waf_logs WHERE {where} GROUP BY {col}"


def _count_dimension_groups(client, dimension: str, where: str, params: dict) -> int:
    inner = _dimension_groups_inner_sql(dimension, where)
    total = client.query(
        f"SELECT count() FROM ({inner})",
        parameters=params,
    ).result_rows[0][0]
    return int(total)


_FILTER_FIELDS = frozenset({
    "log_type", "source", "site_id", "client_ip", "rule_id", "rule_name", "action", "mode",
    "blocked", "domain", "geo_country", "geo_region", "geo_city", "geo_isp", "geo_ip_type",
    "geo_asn", "method", "scheme", "http_version", "uri_path", "uri_ext", "referer_host",
    "ip_is_private", "xff_first", "ua", "ua_family", "ua_os", "ua_browser", "bot_name",
    "bot_category", "tls_version", "keyword",
})

_INT_FILTER_FIELDS = frozenset({"site_id", "rule_id", "geo_asn"})
_BOOL_FILTER_FIELDS = frozenset({"blocked", "ip_is_private"})
_FUZZY_FILTER_FIELDS = frozenset({"rule_name", "ua", "keyword"})
_LOG_TABLE = "waf_logs"


def _col(name: str) -> str:
    return f"{_LOG_TABLE}.{name}"


def _parse_filter_conditions(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    conditions: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        field = item.get("field")
        op = item.get("op")
        value = item.get("value")
        if field not in _FILTER_FIELDS or op not in {"eq", "ne", "contains", "not_contains", "like"}:
            continue
        if value is None:
            continue
        if isinstance(value, list):
            values = [str(v).strip() for v in value if str(v).strip()]
            if not values:
                continue
            conditions.append({"field": field, "op": op, "value": values})
            continue
        text = str(value).strip()
        if not text:
            continue
        conditions.append({"field": field, "op": op, "value": text})
    return conditions


def _param_name(base: str, idx: int) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in base)
    return f"f_{safe}_{idx}"


def _append_condition_sql(
    parts: list[str],
    params: dict,
    *,
    field: str,
    op: str,
    value: str | list[str],
    idx: int,
) -> None:
    values = value if isinstance(value, list) else [value]
    if field == "keyword":
        subparts: list[str] = []
        for vidx, raw in enumerate(values):
            pname = _param_name("kw", idx * 10 + vidx)
            expr = (
                f"(positionCaseInsensitive({_col('uri')}, {{{pname}:String}}) > 0 "
                f"OR positionCaseInsensitive({_col('ua')}, {{{pname}:String}}) > 0 "
                f"OR positionCaseInsensitive({_col('domain')}, {{{pname}:String}}) > 0 "
                f"OR positionCaseInsensitive(concat({_col('scheme')}, '://', {_col('domain')}, {_col('uri')}), {{{pname}:String}}) > 0)"
            )
            if op in {"ne", "not_contains"}:
                expr = f"NOT {expr}"
            elif op == "like":
                expr = (
                    f"(positionCaseInsensitive({_col('uri')}, {{{pname}:String}}) > 0 "
                    f"OR positionCaseInsensitive({_col('ua')}, {{{pname}:String}}) > 0 "
                    f"OR positionCaseInsensitive({_col('domain')}, {{{pname}:String}}) > 0 "
                    f"OR positionCaseInsensitive(concat({_col('scheme')}, '://', {_col('domain')}, {_col('uri')}), {{{pname}:String}}) > 0)"
                )
            subparts.append(expr)
            params[pname] = raw
        if subparts:
            joiner = " OR " if op in {"eq", "contains", "like"} else " AND "
            parts.append(f"({joiner.join(subparts)})")
        return

    subparts = []
    for vidx, raw in enumerate(values):
        pname = _param_name(field, idx * 10 + vidx)
        if field in _BOOL_FILTER_FIELDS:
            bool_val = raw.lower() in {"1", "true", "yes"}
            col = _col(field)
            if op == "ne":
                subparts.append(f"{col} != {{{pname}:UInt8}}")
            else:
                subparts.append(f"{col} = {{{pname}:UInt8}}")
            params[pname] = 1 if bool_val else 0
            continue
        if field in _INT_FILTER_FIELDS:
            try:
                int_val = int(raw)
            except ValueError:
                continue
            col = _col(field)
            if op == "ne":
                subparts.append(f"{col} != {{{pname}:UInt32}}")
            else:
                subparts.append(f"{col} = {{{pname}:UInt32}}")
            params[pname] = int_val
            continue

        col = _col(field)
        if op == "eq":
            subparts.append(f"{col} = {{{pname}:String}}")
            params[pname] = raw
        elif op == "ne":
            subparts.append(f"{col} != {{{pname}:String}}")
            params[pname] = raw
        elif op == "contains":
            subparts.append(f"positionCaseInsensitive({col}, {{{pname}:String}}) > 0")
            params[pname] = raw
        elif op == "not_contains":
            subparts.append(f"positionCaseInsensitive({col}, {{{pname}:String}}) = 0")
            params[pname] = raw
        else:  # like
            subparts.append(f"positionCaseInsensitive({col}, {{{pname}:String}}) > 0")
            params[pname] = raw
    if subparts:
        joiner = " OR " if op in {"eq", "contains", "like"} and len(subparts) > 1 else " AND "
        if len(subparts) == 1:
            parts.append(subparts[0])
        else:
            parts.append(f"({joiner.join(subparts)})")


def _append_json_filters(parts: list[str], params: dict, raw: str | None) -> None:
    for idx, condition in enumerate(_parse_filter_conditions(raw)):
        _append_condition_sql(
            parts,
            params,
            field=condition["field"],
            op=condition["op"],
            value=condition["value"],
            idx=idx,
        )


def _where_clause(q: LogQuery | None, start_ts: datetime, end_ts: datetime) -> tuple[str, dict]:
    parts = [f"{_col('ts')} >= {{start:DateTime}}", f"{_col('ts')} <= {{end:DateTime}}"]
    params: dict = {"start": start_ts, "end": end_ts}
    if q is None:
        return " AND ".join(parts), params
    if q.log_type:
        parts.append(f"{_col('log_type')} = {{log_type:String}}")
        params["log_type"] = q.log_type
    if q.source:
        parts.append(f"{_col('source')} = {{source:String}}")
        params["source"] = q.source
    if q.site_id is not None:
        parts.append(f"{_col('site_id')} = {{site_id:UInt32}}")
        params["site_id"] = q.site_id
    if q.client_ip:
        parts.append(f"{_col('client_ip')} = {{client_ip:String}}")
        params["client_ip"] = q.client_ip
    if q.rule_id is not None:
        parts.append(f"{_col('rule_id')} = {{rule_id:UInt32}}")
        params["rule_id"] = q.rule_id
    if q.rule_name:
        parts.append(f"positionCaseInsensitive({_col('rule_name')}, {{rule_name:String}}) > 0")
        params["rule_name"] = q.rule_name
    if q.action:
        parts.append(f"{_col('action')} = {{action:String}}")
        params["action"] = q.action
    if q.mode:
        parts.append(f"{_col('mode')} = {{mode:String}}")
        params["mode"] = q.mode
    if q.blocked is not None:
        parts.append(f"{_col('blocked')} = {{blocked:UInt8}}")
        params["blocked"] = 1 if q.blocked else 0
    if q.domain:
        parts.append(f"{_col('domain')} = {{domain:String}}")
        params["domain"] = q.domain
    if q.geo_country:
        parts.append(f"{_col('geo_country')} = {{geo_country:String}}")
        params["geo_country"] = q.geo_country
    if q.geo_region:
        parts.append(f"{_col('geo_region')} = {{geo_region:String}}")
        params["geo_region"] = q.geo_region
    if q.geo_city:
        parts.append(f"{_col('geo_city')} = {{geo_city:String}}")
        params["geo_city"] = q.geo_city
    if q.geo_isp:
        parts.append(f"{_col('geo_isp')} = {{geo_isp:String}}")
        params["geo_isp"] = q.geo_isp
    if q.geo_ip_type:
        parts.append(f"{_col('geo_ip_type')} = {{geo_ip_type:String}}")
        params["geo_ip_type"] = q.geo_ip_type
    if q.geo_asn is not None:
        parts.append(f"{_col('geo_asn')} = {{geo_asn:UInt32}}")
        params["geo_asn"] = q.geo_asn
    if q.method:
        parts.append(f"{_col('method')} = {{method:String}}")
        params["method"] = q.method
    if q.scheme:
        parts.append(f"{_col('scheme')} = {{scheme:String}}")
        params["scheme"] = q.scheme
    if q.http_version:
        parts.append(f"{_col('http_version')} = {{http_version:String}}")
        params["http_version"] = q.http_version
    if q.uri_path:
        parts.append(f"{_col('uri_path')} = {{uri_path:String}}")
        params["uri_path"] = q.uri_path
    if q.uri_ext:
        parts.append(f"{_col('uri_ext')} = {{uri_ext:String}}")
        params["uri_ext"] = q.uri_ext
    if q.referer_host:
        parts.append(f"{_col('referer_host')} = {{referer_host:String}}")
        params["referer_host"] = q.referer_host
    if q.ip_is_private is not None:
        parts.append(f"{_col('ip_is_private')} = {{ip_is_private:UInt8}}")
        params["ip_is_private"] = 1 if q.ip_is_private else 0
    if q.xff_first:
        parts.append(f"{_col('xff_first')} = {{xff_first:String}}")
        params["xff_first"] = q.xff_first
    if q.ua:
        parts.append(f"positionCaseInsensitive({_col('ua')}, {{ua:String}}) > 0")
        params["ua"] = q.ua
    if q.ua_family:
        parts.append(f"{_col('ua_family')} = {{ua_family:String}}")
        params["ua_family"] = q.ua_family
    if q.ua_os:
        parts.append(f"{_col('ua_os')} = {{ua_os:String}}")
        params["ua_os"] = q.ua_os
    if q.ua_browser:
        parts.append(f"{_col('ua_browser')} = {{ua_browser:String}}")
        params["ua_browser"] = q.ua_browser
    if q.bot_name:
        parts.append(f"{_col('bot_name')} = {{bot_name:String}}")
        params["bot_name"] = q.bot_name
    if q.bot_category:
        parts.append(f"{_col('bot_category')} = {{bot_category:String}}")
        params["bot_category"] = q.bot_category
    if q.tls_version:
        parts.append(f"{_col('tls_version')} = {{tls_version:String}}")
        params["tls_version"] = q.tls_version
    if q.keyword:
        parts.append(
            f"(positionCaseInsensitive({_col('uri')}, {{kw:String}}) > 0 "
            f"OR positionCaseInsensitive({_col('ua')}, {{kw:String}}) > 0 "
            f"OR positionCaseInsensitive({_col('domain')}, {{kw:String}}) > 0 "
            f"OR positionCaseInsensitive(concat({_col('scheme')}, '://', {_col('domain')}, {_col('uri')}), {{kw:String}}) > 0)"
        )
        params["kw"] = q.keyword
    _append_json_filters(parts, params, q.filters)
    return " AND ".join(parts), params


def _log_id(item: dict) -> str:
    rid = item.get("request_id")
    if rid:
        return str(rid)
    return str(item.get("ts"))


def _row_to_log_item(row: dict) -> dict:
    item = dict(row)
    item["id"] = _log_id(item)
    item["blocked"] = bool(item.get("blocked"))
    payload_raw = item.pop("payload", "{}")
    evaluated_raw = item.pop("evaluated", "{}")
    try:
        payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
        if not isinstance(payload, dict):
            payload = {}
        evaluated = json.loads(evaluated_raw) if isinstance(evaluated_raw, str) else evaluated_raw
        if isinstance(evaluated, list) and evaluated:
            payload["evaluated"] = evaluated
        item["payload"] = payload or None
    except (json.JSONDecodeError, TypeError):
        item["payload"] = None
    return item


async def query_logs(q: LogQuery) -> tuple[int, list[dict]]:
    start_ts, end_ts = _window(q.start, q.end, 24)
    where, params = _where_clause(q, start_ts, end_ts)
    client = get_clickhouse()
    total = client.query(
        f"SELECT count() FROM waf_logs WHERE {where}",
        parameters=params,
    ).result_rows[0][0]
    offset = (q.page - 1) * q.page_size
    rows = client.query(
        f"SELECT * FROM waf_logs WHERE {where} ORDER BY ts DESC "
        f"LIMIT {int(q.page_size)} OFFSET {offset}",
        parameters=params,
    ).named_results()
    items = [_row_to_log_item(dict(row)) for row in rows]
    return int(total), items


async def get_log(log_id: str) -> dict | None:
    def _fetch() -> dict | None:
        client = get_clickhouse()
        rows = list(
            client.query(
                "SELECT * FROM waf_logs WHERE request_id = {rid:String} ORDER BY ts DESC LIMIT 1",
                parameters={"rid": log_id},
            ).named_results()
        )
        if not rows:
            return None
        return _row_to_log_item(dict(rows[0]))

    return await asyncio.to_thread(_fetch)


async def stats_overview(
    *,
    hours: int = 24,
    start: datetime | None = None,
    end: datetime | None = None,
    q: LogQuery | None = None,
) -> dict:
    start_ts, end_ts = _window(start, end, hours)

    def _fetch():
        where, params = _where_clause(q, start_ts, end_ts)
        client = get_clickhouse()
        total = client.query(
            f"SELECT count() FROM waf_logs WHERE {where}", parameters=params
        ).result_rows[0][0]
        blocked = client.query(
            f"SELECT count() FROM waf_logs WHERE {where} AND {_col('blocked')} = 1",
            parameters=params,
        ).result_rows[0][0]
        passed = int(total) - int(blocked)
        unique_ips = client.query(
            f"SELECT uniqExact(client_ip) FROM waf_logs WHERE {where} AND client_ip != ''",
            parameters=params,
        ).result_rows[0][0]
        unique_rules = client.query(
            f"SELECT uniqExact((rule_id, source)) FROM waf_logs WHERE {where} AND rule_id IS NOT NULL",
            parameters=params,
        ).result_rows[0][0]
        window = end_ts - start_ts
        bucket = "toStartOfHour(ts)" if window <= timedelta(days=2) else "toDate(ts)"
        trend_rows = client.query(
            f"SELECT {bucket} AS t, count() AS total, countIf({_col('blocked')} = 1) AS blocked_cnt "
            f"FROM waf_logs WHERE {where} GROUP BY t ORDER BY t",
            parameters=params,
        ).result_rows
        top_rules = client.query(
            f"SELECT rule_id, source, anyLast(rule_name) AS rule_name, count() AS c "
            f"FROM waf_logs WHERE {where} AND rule_id IS NOT NULL "
            f"GROUP BY rule_id, source ORDER BY c DESC LIMIT 10",
            parameters=params,
        ).result_rows
        top_ips = client.query(
            f"SELECT client_ip, count() AS c FROM waf_logs WHERE {where} "
            f"AND client_ip != '' GROUP BY client_ip ORDER BY c DESC LIMIT 10",
            parameters=params,
        ).result_rows
        top_domains = client.query(
            f"SELECT domain, count() AS c FROM waf_logs WHERE {where} "
            f"AND domain != '' GROUP BY domain ORDER BY c DESC LIMIT 8",
            parameters=params,
        ).result_rows
        top_countries = client.query(
            f"SELECT geo_country, count() AS c FROM waf_logs WHERE {where} "
            f"AND geo_country != '' GROUP BY geo_country ORDER BY c DESC LIMIT 8",
            parameters=params,
        ).result_rows
        top_methods = client.query(
            f"SELECT method, count() AS c FROM waf_logs WHERE {where} "
            f"AND method != '' GROUP BY method ORDER BY c DESC LIMIT 6",
            parameters=params,
        ).result_rows
        mode_split = client.query(
            f"SELECT mode, count() AS c FROM waf_logs WHERE {where} GROUP BY mode",
            parameters=params,
        ).result_rows
        source_split = client.query(
            f"SELECT source, count() AS c FROM waf_logs WHERE {where} "
            f"AND source != '' GROUP BY source ORDER BY c DESC",
            parameters=params,
        ).result_rows
        log_type_split = client.query(
            f"SELECT log_type, count() AS c FROM waf_logs WHERE {where} "
            f"AND log_type != '' GROUP BY log_type ORDER BY c DESC",
            parameters=params,
        ).result_rows
        return {
            "start": start_ts.isoformat(),
            "end": end_ts.isoformat(),
            "window_hours": hours,
            "total": int(total),
            "blocked": int(blocked),
            "passed": passed,
            "block_rate": round((int(blocked) / int(total)) * 100, 2) if total else 0.0,
            "unique_ips": int(unique_ips),
            "unique_rules": int(unique_rules),
            "trend": [
                {
                    "time": str(r[0]),
                    "count": int(r[1]),
                    "total": int(r[1]),
                    "blocked": int(r[2]),
                    "passed": int(r[1]) - int(r[2]),
                }
                for r in trend_rows
            ],
            "top_rules_rows": top_rules,
            "top_ips": [{"ip": r[0], "count": r[1]} for r in top_ips],
            "top_domains": [{"domain": r[0], "count": r[1]} for r in top_domains],
            "top_countries": [
                {
                    "country": r[0],
                    "label": format_dimension_label("geo_country", str(r[0]), str(r[0])),
                    "count": r[1],
                }
                for r in top_countries
            ],
            "top_methods": [{"method": r[0], "count": r[1]} for r in top_methods],
            "mode_split": [
                {
                    "mode": r[0] or "unknown",
                    "label": format_dimension_label("mode", str(r[0] or "unknown"), str(r[0] or "unknown")),
                    "count": r[1],
                }
                for r in mode_split
            ],
            "source_split": [
                {
                    "source": r[0] or "unknown",
                    "label": format_dimension_label("source", str(r[0] or "unknown"), str(r[0] or "unknown")),
                    "count": r[1],
                }
                for r in source_split
            ],
            "log_type_split": [
                {
                    "log_type": r[0] or "unknown",
                    "label": format_dimension_label("log_type", str(r[0] or "unknown"), str(r[0] or "unknown")),
                    "count": r[1],
                }
                for r in log_type_split
            ],
        }

    raw = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=10)
    top_rows = raw.pop("top_rules_rows", [])
    refs = [(source, int(rule_id)) for rule_id, source, _, _ in top_rows if rule_id is not None]
    snapshots = {
        _rule_ref(source, int(rule_id)): snapshot
        for rule_id, source, snapshot, _ in top_rows
        if rule_id is not None
    }
    label_map = await _rule_label_map(refs, snapshots=snapshots)
    raw["top_rules"] = [
        {
            "id": rule_id,
            "source": source,
            "name": _pick_rule_name(source, int(rule_id), snapshot, label_map),
            "count": int(count),
        }
        for rule_id, source, snapshot, count in top_rows
    ]
    return raw


async def stats_by_dimension(
    *,
    dimension: str,
    hours: int = 24,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
    limit: int | None = None,
    q: LogQuery | None = None,
) -> LogStatsGroupOut:
    if dimension not in STATS_DIMENSIONS:
        raise ValueError(f"不支持的统计维度: {dimension}")

    start_ts, end_ts = _window(start, end, hours)
    where, params = _where_clause(q, start_ts, end_ts)
    if limit is not None:
        page_size = limit
    page, page_size, page_clause = _paginate(page, page_size)
    client = get_clickhouse()
    group_total = _count_dimension_groups(client, dimension, where, params)

    if dimension == "bot_category":
        async with SessionLocal() as db:
            set_bot_category_labels(await category_label_map(db))

    if dimension == "rule_id":
        rows = client.query(
            f"SELECT rule_id, source, anyLast(rule_name) AS rule_name, count() AS c "
            f"FROM waf_logs WHERE {where} AND rule_id IS NOT NULL "
            f"GROUP BY rule_id, source ORDER BY c DESC {page_clause}",
            parameters=params,
        ).result_rows
        refs = [(source, int(rule_id)) for rule_id, source, _, _ in rows if rule_id is not None]
        snapshots = {
            _rule_ref(source, int(rule_id)): snapshot
            for rule_id, source, snapshot, _ in rows
            if rule_id is not None
        }
        label_map = await _rule_label_map(refs, snapshots=snapshots)
        items = []
        for rule_id, source, snapshot, count in rows:
            if rule_id is None:
                key, label = "none", "未关联规则"
            else:
                src = source or "unknown"
                key = f"{src}:{rule_id}"
                label = format_rule_stats_label(
                    rule_id=rule_id,
                    rule_name=_pick_rule_name(source, int(rule_id), snapshot, label_map),
                    source=source,
                )
            items.append(LogStatsGroupItem(key=key, label=label, count=int(count)))
    elif dimension == "site_id":
        rows = client.query(
            f"SELECT site_id, anyLast(domain) AS domain_snapshot, count() AS c "
            f"FROM waf_logs WHERE {where} "
            f"GROUP BY site_id ORDER BY c DESC {page_clause}",
            parameters=params,
        ).result_rows
        site_ids = [int(site_id) for site_id, _, _ in rows if site_id is not None]
        site_labels = await _site_label_map(site_ids)
        items = []
        for site_id, domain_snapshot, count in rows:
            if site_id is None:
                key, label = "none", "（空）"
            else:
                key = str(site_id)
                name, domain = _pick_site_display(int(site_id), domain_snapshot, site_labels)
                label = format_dimension_label(
                    "site_id",
                    key,
                    f"站点 #{site_id}",
                    site_name=name,
                    site_domain=domain,
                )
            items.append(LogStatsGroupItem(key=key, label=label, count=int(count)))
    elif dimension == "query_count_bucket":
        rows = client.query(
            f"SELECT multiIf(query_count = 0, '0', query_count <= 5, '1-5', "
            f"query_count <= 20, '6-20', '20+') AS bucket, count() AS c "
            f"FROM waf_logs WHERE {where} GROUP BY bucket ORDER BY c DESC {page_clause}",
            parameters=params,
        ).result_rows
        items = [
            LogStatsGroupItem(key=str(b), label=str(b), count=int(c)) for b, c in rows
        ]
    elif dimension == "hour_of_day":
        rows = client.query(
            f"SELECT toHour(ts) AS h, count() AS c FROM waf_logs WHERE {where} "
            f"GROUP BY h ORDER BY h {page_clause}",
            parameters=params,
        ).result_rows
        items = [
            LogStatsGroupItem(key=str(h), label=f"{h}:00", count=int(c)) for h, c in rows
        ]
    elif dimension == "weekday":
        rows = client.query(
            f"SELECT toDayOfWeek(ts) AS d, count() AS c FROM waf_logs WHERE {where} "
            f"GROUP BY d ORDER BY d {page_clause}",
            parameters=params,
        ).result_rows
        names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        items = [
            LogStatsGroupItem(key=str(d), label=names[int(d)] if d else str(d), count=int(c))
            for d, c in rows
        ]
    elif dimension == "blocked":
        rows = client.query(
            f"SELECT blocked, count() AS c FROM waf_logs WHERE {where} "
            f"GROUP BY blocked ORDER BY c DESC {page_clause}",
            parameters=params,
        ).result_rows
        items = []
        for val, count in rows:
            key = "true" if val else "false"
            label = "已拦截" if val else "已放行"
            items.append(LogStatsGroupItem(key=key, label=label, count=int(count)))
    elif dimension == "full_url":
        rows = client.query(
            f"SELECT concat(scheme, '://', domain, uri) AS full_url, count() AS c "
            f"FROM waf_logs WHERE {where} AND domain != '' AND uri != '' "
            f"GROUP BY full_url ORDER BY c DESC {page_clause}",
            parameters=params,
        ).result_rows
        items = []
        for val, count in rows:
            if val is None or val == "":
                key, raw = "none", "（空）"
            else:
                key, raw = str(val), str(val)
            label = format_dimension_label(dimension, key, raw)
            items.append(LogStatsGroupItem(key=key, label=label, count=int(count)))
    else:
        col = _DIM_COLUMN.get(dimension, dimension)
        rows = client.query(
            f"SELECT {col}, count() AS c FROM waf_logs WHERE {where} "
            f"GROUP BY {col} ORDER BY c DESC {page_clause}",
            parameters=params,
        ).result_rows
        items = []
        for val, count in rows:
            if val is None or val == "":
                key, raw = "none", "（空）"
            else:
                key, raw = str(val), str(val)
            label = format_dimension_label(dimension, key, raw)
            items.append(LogStatsGroupItem(key=key, label=label, count=int(count)))

    total = client.query(
        f"SELECT count() FROM waf_logs WHERE {where}", parameters=params
    ).result_rows[0][0]
    return LogStatsGroupOut(
        dimension=dimension,
        start=start_ts,
        end=end_ts,
        total=int(total),
        group_total=group_total,
        page=page,
        page_size=page_size,
        items=items,
    )
