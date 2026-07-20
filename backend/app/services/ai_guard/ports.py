"""Port adapters: bridge AI Guard to core WAF services without coupling LLM into core."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.fields import field_map, validate_condition
from app.models import IpList, RateLimit, Rule, Site
from app.models.notification import NotificationChannel
from app.models.rule import MODES
from app.schemas.ip_list import IpListCreate
from app.schemas.rate_limit import RateLimitCreate
from app.schemas.rule import RuleCreate
from app.schemas.site import SiteCreate
from app.services import nginx_conf, rule_sync
from app.services.ai_guard.log_query import build_log_query_from_tool_args
from app.services.logging.query_clickhouse import query_logs as ch_query_logs
from app.services.logging.query_clickhouse import stats_by_dimension, stats_overview
from app.services.notifications.channels import send_via_channel
from app.services.site_scope import apply_site_scope
from app.services.site_domains import site_domain_list

log = logging.getLogger("waf.ai_guard.ports")
_FIELDS = field_map()
_BLOCK_PAGE_KEYS = ("custom_block_page_enabled", "block_page_status_code", "block_page_html")


def _block_page_payload(payload: dict) -> dict:
    return {k: payload[k] for k in _BLOCK_PAGE_KEYS if k in payload}


class AiResourceWriter:
    """Execute validated CRUD writes on behalf of AI (after user confirmation)."""

    async def list_sites(self, db: AsyncSession) -> list[dict]:
        rows = (await db.execute(select(Site).order_by(Site.id.desc()).limit(100))).scalars().all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "domain": s.domain,
                "domains": site_domain_list(s),
                "enabled": s.enabled,
            }
            for s in rows
        ]

    async def list_rules(
        self, db: AsyncSession, *, site_id: int | None = None, limit: int = 20
    ) -> list[dict]:
        q = select(Rule).order_by(Rule.priority.asc()).limit(limit)
        rows = (await db.execute(q)).scalars().all()
        items = []
        for r in rows:
            ids = r.site_ids or []
            if site_id is not None and ids and site_id not in ids:
                continue
            items.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "mode": r.mode,
                    "priority": r.priority,
                    "site_ids": ids,
                    "enabled": r.enabled,
                    "custom_block_page_enabled": r.custom_block_page_enabled,
                }
            )
        return items

    async def list_rate_limits(
        self, db: AsyncSession, *, site_id: int | None = None, limit: int = 20
    ) -> list[dict]:
        rows = (
            await db.execute(
                select(RateLimit).order_by(RateLimit.priority.asc(), RateLimit.id.asc()).limit(limit)
            )
        ).scalars().all()
        items = []
        for r in rows:
            ids = r.site_ids or []
            if site_id is not None and ids and site_id not in ids:
                continue
            items.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "priority": r.priority,
                    "keys": r.keys,
                    "window": r.window,
                    "threshold": r.threshold,
                    "mode": r.mode,
                    "site_ids": ids,
                    "enabled": r.enabled,
                    "has_conditions": bool(r.conditions),
                }
            )
        return items

    def _validate_rate_limit_keys(self, keys: list | None) -> list[dict]:
        normalized: list[dict] = []
        for key in keys or [{"field": "ip.src"}]:
            field = key.get("field") if isinstance(key, dict) else getattr(key, "field", None)
            if field not in _FIELDS:
                raise ValueError(f"未知限速字段: {field}")
            item: dict = {"field": field}
            arg = key.get("arg") if isinstance(key, dict) else getattr(key, "arg", None)
            if arg:
                item["arg"] = arg
            normalized.append(item)
        return normalized

    async def preview_rate_limit(self, payload: dict) -> dict:
        mode = payload.get("mode", "block")
        if mode not in MODES:
            raise ValueError(f"无效的防护方式: {mode}")
        window = int(payload.get("window") or 0)
        threshold = int(payload.get("threshold") or 0)
        if window <= 0:
            raise ValueError("window 必须大于 0")
        if threshold <= 0:
            raise ValueError("threshold 必须大于 0")
        keys = self._validate_rate_limit_keys(payload.get("keys"))
        conditions = None
        if payload.get("conditions"):
            conditions = validate_condition(payload["conditions"])
        RateLimitCreate.model_validate(
            {
                "name": payload.get("name") or "preview",
                "priority": payload.get("priority", 100),
                "keys": keys,
                "window": window,
                "threshold": threshold,
                "mode": mode,
                "conditions": conditions,
            }
        )
        return {
            "valid": True,
            "keys": keys,
            "window": window,
            "threshold": threshold,
            "mode": mode,
            "conditions": conditions,
        }

    async def create_rate_limit(self, db: AsyncSession, payload: dict) -> dict:
        preview = await self.preview_rate_limit(payload)
        data = apply_site_scope(
            {
                "name": payload["name"],
                "priority": payload.get("priority", 100),
                "keys": preview["keys"],
                "window": preview["window"],
                "threshold": preview["threshold"],
                "mode": preview["mode"],
                "site_ids": payload.get("site_ids"),
                "enabled": payload.get("enabled", True),
                "conditions": preview["conditions"],
                "remark": payload.get("remark"),
                **_block_page_payload(payload),
            }
        )
        RateLimitCreate.model_validate(data)
        row = RateLimit(**data)
        db.add(row)
        await db.commit()
        await db.refresh(row)
        await rule_sync.publish(db)
        return {
            "id": row.id,
            "name": row.name,
            "window": row.window,
            "threshold": row.threshold,
            "mode": row.mode,
        }

    async def query_logs(self, arguments: dict) -> dict:
        q = build_log_query_from_tool_args(arguments)
        total, items = await ch_query_logs(q)
        return {
            "total": total,
            "returned": len(items),
            "page": q.page,
            "page_size": q.page_size,
            "start": q.start.isoformat() if q.start else None,
            "end": q.end.isoformat() if q.end else None,
            "filters_applied": {
                "site_id": q.site_id,
                "blocked": q.blocked,
                "keyword": q.keyword,
                "filters": q.filters,
            },
            "logs": [_sanitize_log_item(item) for item in items],
        }

    async def get_log_stats(self, arguments: dict) -> dict:
        q = build_log_query_from_tool_args({**arguments, "limit": 1, "page": 1})
        hours = int(arguments.get("hours") or 24)
        hours = min(max(1, hours), 168)
        data = await stats_overview(
            hours=hours,
            start=q.start,
            end=q.end,
            q=q,
            trend_granularity=arguments.get("trend_granularity"),
        )
        return data

    async def query_log_stats_group(self, arguments: dict) -> dict:
        dimension = arguments.get("dimension")
        if not dimension:
            raise ValueError("dimension 为必填参数")
        q = build_log_query_from_tool_args({**arguments, "limit": 1, "page": 1})
        hours = int(arguments.get("hours") or 24)
        hours = min(max(1, hours), 168)
        limit = min(max(1, int(arguments.get("limit") or 20)), 100)
        data = await stats_by_dimension(
            dimension=str(dimension),
            hours=hours,
            start=q.start,
            end=q.end,
            page=1,
            page_size=limit,
            limit=limit,
            q=q,
        )
        return data.model_dump()

    async def preview_rule(self, payload: dict) -> dict:
        conditions = validate_condition(payload.get("conditions"))
        mode = payload.get("mode", "observe")
        if mode not in MODES:
            raise ValueError(f"无效的防护方式: {mode}")
        RuleCreate.model_validate(
            {
                "name": payload.get("name") or "preview",
                "mode": mode,
                "priority": payload.get("priority", 100),
                "conditions": conditions,
                **_block_page_payload(payload),
            }
        )
        return {"valid": True, "conditions": conditions, "mode": mode}

    async def create_site(self, db: AsyncSession, payload: dict) -> dict:
        from sqlalchemy import select

        body = SiteCreate.model_validate(payload)
        try:
            from app.services.site_domains import ensure_domains_available

            await ensure_domains_available(db, body.domains)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if not body.listen_http and not body.listen_https:
            raise ValueError("至少需要开启 HTTP 或 HTTPS 监听")
        if body.listen_https and not body.certificate_id:
            raise ValueError("开启 HTTPS 时必须选择 SSL 证书")
        if body.certificate_id:
            from app.models import Certificate

            cert = await db.get(Certificate, body.certificate_id)
            if cert is None:
                raise ValueError("所选证书不存在")
        payload_data = body.model_dump()
        domains = payload_data.pop("domains")
        from app.services.site_domains import apply_domains_to_site

        site = Site(**payload_data)
        apply_domains_to_site(site, domains)
        db.add(site)
        await db.commit()
        await db.refresh(site)
        await rule_sync.publish(db)
        await nginx_conf.regenerate(db)
        return {"id": site.id, "name": site.name, "domain": site.domain, "domains": domains}

    async def create_rule(self, db: AsyncSession, payload: dict) -> dict:
        body = RuleCreate.model_validate(
            {
                **payload,
                "conditions": validate_condition(payload.get("conditions")),
            }
        )
        if body.mode not in MODES:
            raise ValueError(f"无效的防护方式: {body.mode}")
        data = apply_site_scope(body.model_dump())
        rule = Rule(**data)
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        await rule_sync.publish(db)
        return {"id": rule.id, "name": rule.name, "mode": rule.mode}

    async def create_whitelist_entry(self, db: AsyncSession, payload: dict) -> dict:
        payload = dict(payload)
        payload["list_type"] = "white"
        conditions = validate_condition(payload.get("conditions"))
        data = apply_site_scope(
            {
                "list_type": "white",
                "name": payload["name"],
                "site_ids": payload.get("site_ids"),
                "enabled": payload.get("enabled", True),
                "conditions": conditions,
                "remark": payload.get("remark"),
                **_block_page_payload(payload),
            }
        )
        IpListCreate.model_validate({**data, "list_type": "white"})
        row = IpList(**data)
        db.add(row)
        await db.commit()
        await db.refresh(row)
        await rule_sync.publish(db)
        return {"id": row.id, "name": row.name}

    async def delete_rule(self, db: AsyncSession, rule_id: int) -> None:
        rule = await db.get(Rule, rule_id)
        if rule is None:
            raise ValueError("规则不存在")
        await db.delete(rule)
        await db.commit()
        await rule_sync.publish(db)

    async def validate_tool_arguments(self, tool_name: str, arguments: dict) -> dict:
        """Validate tool payloads without persisting (for pending confirmations)."""
        if tool_name == "create_site":
            SiteCreate.model_validate(arguments)
            return {"valid": True}
        if tool_name == "create_rule":
            return await self.preview_rule(arguments)
        if tool_name == "create_whitelist_entry":
            payload = dict(arguments)
            payload["list_type"] = "white"
            conditions = validate_condition(payload.get("conditions"))
            IpListCreate.model_validate({**payload, "conditions": conditions})
            return {"valid": True, "conditions": conditions}
        if tool_name == "create_rate_limit":
            return await self.preview_rate_limit(arguments)
        return {"valid": True}

    async def execute_tool(
        self, db: AsyncSession, tool_name: str, arguments: dict, *, dry_run: bool = False
    ) -> dict:
        if tool_name == "list_sites":
            return {"sites": await self.list_sites(db)}
        if tool_name == "list_rules":
            return {
                "rules": await self.list_rules(
                    db,
                    site_id=arguments.get("site_id"),
                    limit=int(arguments.get("limit") or 20),
                )
            }
        if tool_name == "list_rate_limits":
            return {
                "rate_limits": await self.list_rate_limits(
                    db,
                    site_id=arguments.get("site_id"),
                    limit=int(arguments.get("limit") or 20),
                )
            }
        if tool_name == "query_logs":
            return await self.query_logs(arguments)
        if tool_name == "get_log_stats":
            return await self.get_log_stats(arguments)
        if tool_name == "query_log_stats_group":
            return await self.query_log_stats_group(arguments)
        if tool_name == "preview_rule":
            return await self.preview_rule(arguments)
        if tool_name == "preview_rate_limit":
            return await self.preview_rate_limit(arguments)
        if dry_run:
            validation = await self.validate_tool_arguments(tool_name, arguments)
            return {
                "preview": True,
                "tool": tool_name,
                "arguments": arguments,
                **validation,
            }
        if tool_name == "create_site":
            return await self.create_site(db, arguments)
        if tool_name == "create_rule":
            return await self.create_rule(db, arguments)
        if tool_name == "create_rate_limit":
            return await self.create_rate_limit(db, arguments)
        if tool_name == "create_whitelist_entry":
            return await self.create_whitelist_entry(db, arguments)
        raise ValueError(f"未知工具: {tool_name}")


class LogSampler:
    """Sample recent logs from ClickHouse for defense analysis."""

    async def sample(
        self,
        *,
        window_min: int = 5,
        site_id: int | None = None,
        max_rows: int = 200,
    ) -> tuple[list[dict], dict]:
        return await asyncio.to_thread(
            self._sample_sync, window_min, site_id, max_rows
        )

    def _sample_sync(
        self, window_min: int, site_id: int | None, max_rows: int
    ) -> tuple[list[dict], dict]:
        from app.core.clickhouse import get_clickhouse

        clauses = ["ts >= now() - INTERVAL {mins:UInt16} MINUTE"]
        params: dict = {"mins": window_min, "limit": max_rows}
        if site_id is not None:
            clauses.append("site_id = {site_id:UInt32}")
            params["site_id"] = site_id
        where = " AND ".join(clauses)
        client = get_clickhouse()

        blocked_rows = list(
            client.query(
                f"SELECT request_id, client_ip, method, request_uri, domain, blocked, "
                f"rule_name, mode, geo_country, ua_family, log_type "
                f"FROM waf_logs WHERE {where} AND blocked = 1 "
                f"ORDER BY ts DESC LIMIT {{limit:UInt32}}",
                parameters=params,
            ).named_results()
        )

        blocked_count = len(blocked_rows)
        remaining = max(0, max_rows - blocked_count)
        passed_rows: list[dict] = []
        if remaining > 0:
            params["limit"] = remaining
            passed_rows = list(
                client.query(
                    f"SELECT request_id, client_ip, method, request_uri, domain, blocked, "
                    f"rule_name, mode, geo_country, ua_family, log_type "
                    f"FROM waf_logs WHERE {where} AND blocked = 0 "
                    f"ORDER BY ts DESC LIMIT {{limit:UInt32}}",
                    parameters=params,
                ).named_results()
            )

        rows = [dict(r) for r in blocked_rows] + [dict(r) for r in passed_rows]
        meta = self._aggregate(rows, window_min)
        return rows, meta

    def _aggregate(self, rows: list[dict], window_min: int) -> dict:
        from collections import Counter

        ips = Counter(str(r.get("client_ip") or "") for r in rows)
        uris = Counter(str(r.get("request_uri") or r.get("uri") or "")[:120] for r in rows)
        methods = Counter(str(r.get("method") or "") for r in rows)
        blocked = sum(1 for r in rows if r.get("blocked"))
        return {
            "window_min": window_min,
            "sampled": len(rows),
            "blocked_count": blocked,
            "passed_count": len(rows) - blocked,
            "top_ips": ips.most_common(10),
            "top_uris": uris.most_common(10),
            "methods": dict(methods),
        }


class AiNotifier:
    """Send staged notifications via configured channels."""

    async def notify_policy(
        self,
        db: AsyncSession,
        *,
        channel_ids: list[int],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> list[dict]:
        if not channel_ids:
            return []
        channels = (
            await db.execute(
                select(NotificationChannel).where(
                    NotificationChannel.id.in_(channel_ids),
                    NotificationChannel.enabled.is_(True),
                )
            )
        ).scalars().all()
        log_entries = []
        for ch in channels:
            entry = {"channel_id": ch.id, "status": "failed", "at": datetime.utcnow().isoformat()}
            try:
                if ch.channel_type == "email":
                    await send_via_channel(
                        ch, subject=subject, body=body, html_body=html_body
                    )
                else:
                    await send_via_channel(ch, subject=subject, body=body)
                entry["status"] = "sent"
            except Exception as exc:  # noqa: BLE001
                entry["detail"] = str(exc)
                log.exception("ai guard notify channel=%s failed", ch.id)
            log_entries.append(entry)
        return log_entries


def compact_log_rows(rows: list[dict], limit: int = 80) -> list[dict]:
    """Strip sensitive fields and truncate for LLM prompt."""
    return [_sanitize_log_item(r) for r in rows[:limit]]


def _sanitize_log_item(item: dict) -> dict:
    return {
        "ts": str(item.get("ts") or ""),
        "client_ip": item.get("client_ip"),
        "method": item.get("method"),
        "domain": item.get("domain"),
        "request_uri": (item.get("request_uri") or item.get("uri") or "")[:200],
        "uri_path": item.get("uri_path"),
        "blocked": bool(item.get("blocked")),
        "source": item.get("source"),
        "rule_id": item.get("rule_id"),
        "rule_name": item.get("rule_name"),
        "mode": item.get("mode"),
        "action": item.get("action"),
        "site_id": item.get("site_id"),
        "geo_country": item.get("geo_country"),
        "ua_family": item.get("ua_family"),
        "log_type": item.get("log_type"),
    }


writer = AiResourceWriter()
log_sampler = LogSampler()
notifier = AiNotifier()
