"""Evaluate whether AI Guard policies should fire."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.ai_guard import AiGuardPolicy
from app.services.traffic_intel.constants import REDIS_SNAPSHOT_KEY
from app.services.traffic_intel.types import AnomalyResult

log = logging.getLogger("waf.ai_guard.trigger")


async def _snapshot_qps(window_sec: int) -> tuple[float, int]:
    redis = get_redis()
    raw = await redis.get(REDIS_SNAPSHOT_KEY)
    if not raw:
        return 0.0, 0
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return 0.0, 0
    for w in data.get("global", {}).get("windows") or []:
        if int(w.get("sec", 0)) == window_sec:
            requests = int(w.get("requests") or 0)
            qps = float(w.get("qps") or (requests / max(window_sec, 1)))
            return qps, requests
    return 0.0, 0


async def _block_rate(window_min: int, site_id: int | None) -> tuple[float, int, int]:
    def _query():
        from app.core.clickhouse import get_clickhouse

        clauses = ["ts >= now() - INTERVAL {mins:UInt16} MINUTE"]
        params: dict = {"mins": window_min}
        if site_id is not None:
            clauses.append("site_id = {site_id:UInt32}")
            params["site_id"] = site_id
        where = " AND ".join(clauses)
        client = get_clickhouse()
        row = client.query(
            f"SELECT count(), countIf(blocked = 1) FROM waf_logs WHERE {where}",
            parameters=params,
        ).result_rows[0]
        return int(row[0]), int(row[1])

    import asyncio

    total, blocked = await asyncio.to_thread(_query)
    rate = (blocked / total * 100) if total else 0.0
    return rate, total, blocked


def _in_cooldown(policy: AiGuardPolicy) -> bool:
    if not policy.last_triggered_at:
        return False
    return datetime.utcnow() - policy.last_triggered_at < timedelta(seconds=policy.cooldown_sec)


def _matches_filter(policy: AiGuardPolicy, site_id: int | None) -> bool:
    filt = policy.condition_filter or {}
    want_site = filt.get("site_id")
    if want_site is not None and site_id is not None and int(want_site) != site_id:
        return False
    if want_site is not None and site_id is None:
        return False
    return True


async def evaluate_policy(
    db: AsyncSession, policy: AiGuardPolicy, *, anomaly: AnomalyResult | None = None
) -> dict | None:
    if not policy.enabled or _in_cooldown(policy):
        return None

    params = policy.trigger_params or {}
    ttype = policy.trigger_type

    if ttype == "traffic_intel.anomaly":
        if anomaly is None:
            return None
        want = params.get("window_sec")
        if want and int(want) != anomaly.window_sec:
            return None
        site_id = anomaly.site_id
        if not _matches_filter(policy, site_id):
            return None
        return {
            "type": ttype,
            "window_sec": anomaly.window_sec,
            "current_requests": anomaly.current_requests,
            "baseline_avg": anomaly.baseline_avg,
            "message": anomaly.message,
            "site_id": site_id,
            "window_min": 5,
        }

    if ttype == "traffic.qps_gt":
        window_sec = int(params.get("window_sec", 60))
        threshold = float(params.get("qps", 100))
        qps, requests = await _snapshot_qps(window_sec)
        if qps <= threshold:
            return None
        if not _matches_filter(policy, params.get("site_id")):
            return None
        return {
            "type": ttype,
            "window_sec": window_sec,
            "qps": qps,
            "requests": requests,
            "threshold": threshold,
            "window_min": max(1, window_sec // 60),
        }

    if ttype == "traffic.abs_gt":
        window_sec = int(params.get("window_sec", 300))
        threshold = int(params.get("threshold", 1000))
        _, requests = await _snapshot_qps(window_sec)
        if requests <= threshold:
            return None
        if not _matches_filter(policy, params.get("site_id")):
            return None
        return {
            "type": ttype,
            "window_sec": window_sec,
            "requests": requests,
            "threshold": threshold,
            "window_min": max(1, window_sec // 60),
        }

    if ttype == "security.block_rate":
        window_min = int(params.get("window_min", 5))
        percent = float(params.get("percent", 30))
        site_id = params.get("site_id")
        rate, total, blocked = await _block_rate(window_min, site_id)
        if rate <= percent or total <= 0:
            return None
        if not _matches_filter(policy, site_id):
            return None
        return {
            "type": ttype,
            "window_min": window_min,
            "block_rate": rate,
            "total": total,
            "blocked": blocked,
            "percent": percent,
            "site_id": site_id,
        }

    return None


async def list_enabled_policies(db: AsyncSession) -> list[AiGuardPolicy]:
    return list(
        (
            await db.execute(
                select(AiGuardPolicy)
                .where(AiGuardPolicy.enabled.is_(True))
                .order_by(AiGuardPolicy.id)
            )
        ).scalars().all()
    )
