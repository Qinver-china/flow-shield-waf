"""Evaluate alert policies and dispatch notifications."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.alert_conditions import CONDITION_TYPE_MAP
from app.core.redis import get_redis
from app.models.notification import AlertPolicy, NotificationChannel
from app.services.analytics.alert_log_store import AlertLogStore
from app.services.notifications.channels import send_via_channel
from app.services.traffic_intel.constants import REDIS_SNAPSHOT_KEY
from app.services.traffic_intel.detector import AnomalyDetector
from app.services.traffic_intel.store.baseline_mysql import BaselineStore
from app.services.traffic_intel.store.clickhouse import ClickHouseTrafficStore
from app.services.traffic_intel.timezone import get_traffic_timezone
from app.services.traffic_intel.types import TrafficIntelConfig
from app.services.traffic_intel.windows import is_baseline_stable

log = logging.getLogger("waf.notify.evaluator")

TRAFFIC_SNAPSHOT_KEY = REDIS_SNAPSHOT_KEY
_LIVE_WINDOW_THRESHOLD_SEC = 60
_alert_logs = AlertLogStore()


class AlertPolicyEvaluator:
    def __init__(self) -> None:
        self._ch = ClickHouseTrafficStore()
        self._baselines = BaselineStore()
        self._detector = AnomalyDetector(ch_store=self._ch, baseline_store=self._baselines)

    async def run(self, db: AsyncSession) -> int:
        policies = (
            await db.execute(
                select(AlertPolicy).where(AlertPolicy.enabled.is_(True)).order_by(AlertPolicy.id)
            )
        ).scalars().all()
        fired = 0
        for policy in policies:
            if await self._in_cooldown(policy):
                continue
            message = await self._evaluate(policy, db)
            if not message:
                continue
            policy.last_fired_at = datetime.utcnow()
            await self._dispatch(db, policy, message)
            await db.commit()
            fired += 1
        return fired

    async def _in_cooldown(self, policy: AlertPolicy) -> bool:
        if not policy.last_fired_at:
            return False
        return datetime.utcnow() - policy.last_fired_at < timedelta(seconds=policy.cooldown_sec)

    async def _evaluate(self, policy: AlertPolicy, db: AsyncSession) -> str | None:
        ctype = policy.condition_type
        params = policy.condition_params or {}
        meta = CONDITION_TYPE_MAP.get(ctype)
        label = meta["label"] if meta else ctype

        if ctype == "traffic.baseline_gt":
            return await self._traffic_baseline(policy, db, params, direction="gt")
        if ctype == "traffic.baseline_lt":
            return await self._traffic_baseline(policy, db, params, direction="lt")
        if ctype == "traffic.abs_gt":
            return await self._traffic_abs(params, direction="gt", label=label)
        if ctype == "traffic.abs_lt":
            return await self._traffic_abs(params, direction="lt", label=label)
        if ctype == "traffic.qps_gt":
            return await self._traffic_qps(params, direction="gt", label=label)
        if ctype == "traffic.qps_lt":
            return await self._traffic_qps(params, direction="lt", label=label)
        if ctype == "traffic.burst_logging":
            return await self._traffic_burst(label)
        if ctype == "security.block_count":
            return await self._block_count(params, label)
        if ctype == "security.block_rate":
            return await self._block_rate(params, label)
        return None

    async def _traffic_baseline(
        self,
        policy: AlertPolicy,
        db: AsyncSession,
        params: dict,
        *,
        direction: str,
    ) -> str | None:
        window_sec = int(params.get("window_sec", 300))
        percent = float(params.get("percent", 50))
        site_id = params.get("site_id")
        timezone_name = await get_traffic_timezone(db)
        baseline = await self._baselines.get(
            db,
            site_id=site_id,
            window_sec=window_sec,
            as_of=datetime.utcnow(),
            timezone_name=timezone_name,
        )
        if not baseline or baseline.avg_requests <= 0:
            return None
        if not is_baseline_stable(window_sec, baseline.sample_count):
            return None
        current = await self._window_requests(window_sec, site_id=site_id)
        if direction == "gt":
            cfg = TrafficIntelConfig(spike_ratio=percent / 100)
            anomaly = self._detector._compare(  # noqa: SLF001
                current, baseline, cfg, datetime.utcnow()
            )
            if anomaly is None:
                return None
            return f"【{policy.name}】{anomaly.message}"
        threshold = baseline.avg_requests * (1 - percent / 100)
        if current >= threshold:
            return None
        return (
            f"【{policy.name}】{window_sec}s 窗口内当前 {current} 次请求，"
            f"低于基线 {baseline.avg_requests:.0f} 的 {percent:.0f}%"
        )

    async def _traffic_abs(self, params: dict, *, direction: str, label: str) -> str | None:
        window_sec = int(params.get("window_sec", 300))
        threshold = int(params.get("threshold", 0))
        site_id = params.get("site_id")
        current = await self._window_requests(window_sec, site_id=site_id)
        scope = f"站点 #{site_id}" if site_id else "全站"
        if direction == "gt" and current > threshold:
            return (
                f"【预警】{label}：{scope} {window_sec}s 窗口内 {current} 次请求，"
                f"高于阈值 {threshold}"
            )
        if direction == "lt" and current < threshold:
            return (
                f"【预警】{label}：{scope} {window_sec}s 窗口内 {current} 次请求，"
                f"低于阈值 {threshold}"
            )
        return None

    async def _traffic_qps(self, params: dict, *, direction: str, label: str) -> str | None:
        window_sec = int(params.get("window_sec", 300))
        threshold = float(params.get("threshold", 0))
        site_id = params.get("site_id")
        current = await self._window_requests(window_sec, site_id=site_id)
        qps = current / window_sec if window_sec > 0 else 0
        scope = f"站点 #{site_id}" if site_id else "全站"
        if direction == "gt" and qps > threshold:
            return (
                f"【预警】{label}：{scope} {window_sec}s 窗口平均 QPS {qps:.2f}，"
                f"高于阈值 {threshold}"
            )
        if direction == "lt" and qps < threshold:
            return (
                f"【预警】{label}：{scope} {window_sec}s 窗口平均 QPS {qps:.2f}，"
                f"低于阈值 {threshold}"
            )
        return None

    async def _traffic_burst(self, label: str) -> str | None:
        redis = get_redis()
        raw = await redis.get(TRAFFIC_SNAPSHOT_KEY)
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        if data.get("global", {}).get("burst_active"):
            return f"【预警】{label}：系统已进入流量自动取证模式，建议关注攻击日志。"
        return None

    async def _block_count(self, params: dict, label: str) -> str | None:
        window_min = int(params.get("window_min", 5))
        threshold = int(params.get("threshold", 100))
        site_id = params.get("site_id")
        count = await self._query_log_count(window_min, site_id=site_id, blocked_only=True)
        if count > threshold:
            scope = f"站点 #{site_id}" if site_id else "全站"
            return (
                f"【预警】{label}：{scope} 近 {window_min} 分钟拦截 {count} 次，"
                f"超过阈值 {threshold}"
            )
        return None

    async def _block_rate(self, params: dict, label: str) -> str | None:
        window_min = int(params.get("window_min", 5))
        percent = float(params.get("percent", 30))
        site_id = params.get("site_id")
        total, blocked = await self._query_block_stats(window_min, site_id=site_id)
        if total <= 0:
            return None
        rate = blocked / total * 100
        if rate > percent:
            scope = f"站点 #{site_id}" if site_id else "全站"
            return (
                f"【预警】{label}：{scope} 近 {window_min} 分钟拦截率 {rate:.1f}%，"
                f"超过阈值 {percent:.0f}%（{blocked}/{total}）"
            )
        return None

    async def _window_requests(
        self,
        window_sec: int,
        *,
        site_id: int | None,
    ) -> int:
        if window_sec < _LIVE_WINDOW_THRESHOLD_SEC:
            return await self._snapshot_window_requests(window_sec, site_id=site_id)
        return await asyncio.to_thread(
            self._ch.current_window_requests,
            window_sec,
            site_id=site_id,
        )

    async def _snapshot_window_requests(
        self,
        window_sec: int,
        *,
        site_id: int | None = None,
    ) -> int:
        redis = get_redis()
        raw = await redis.get(TRAFFIC_SNAPSHOT_KEY)
        if not raw:
            return 0
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return 0
        if site_id is None:
            windows = data.get("global", {}).get("windows") or []
        else:
            windows = (data.get("sites") or {}).get(str(site_id), {}).get("windows") or []
        for w in windows:
            try:
                if int(w.get("sec", 0)) == window_sec:
                    return int(w.get("requests") or 0)
            except (TypeError, ValueError):
                continue
        return 0

    async def _query_log_count(
        self,
        window_min: int,
        *,
        site_id: int | None,
        blocked_only: bool,
    ) -> int:
        total, blocked = await self._query_block_stats(window_min, site_id=site_id)
        return blocked if blocked_only else total

    async def _query_block_stats(
        self,
        window_min: int,
        *,
        site_id: int | None,
    ) -> tuple[int, int]:
        def _query() -> tuple[int, int]:
            from app.core.clickhouse import get_clickhouse

            clauses = ["ts >= now() - INTERVAL {mins:UInt16} MINUTE"]
            params: dict = {"mins": window_min}
            if site_id is not None:
                clauses.append("site_id = {site_id:UInt32}")
                params["site_id"] = int(site_id)
            where = " AND ".join(clauses)
            client = get_clickhouse()
            row = client.query(
                f"SELECT count(), countIf(blocked = 1) FROM waf_logs WHERE {where}",
                parameters=params,
            ).result_rows
            if not row:
                return 0, 0
            return int(row[0][0]), int(row[0][1])

        return await asyncio.to_thread(_query)

    async def _dispatch(self, db: AsyncSession, policy: AlertPolicy, message: str) -> bool:
        channel_ids = policy.channel_ids or []
        if not channel_ids:
            log.warning("policy %s triggered but no channels configured", policy.id)
            await _alert_logs.insert(
                policy_id=policy.id,
                channel_id=0,
                status="skipped",
                message=message,
                detail="no notification channels configured",
            )
            return False
        channels = (
            await db.execute(
                select(NotificationChannel).where(
                    NotificationChannel.id.in_(channel_ids),
                    NotificationChannel.enabled.is_(True),
                )
            )
        ).scalars().all()
        if not channels:
            await _alert_logs.insert(
                policy_id=policy.id,
                channel_id=0,
                status="skipped",
                message=message,
                detail="no enabled notification channels",
            )
            return False
        subject = f"流盾WAF 预警：{policy.name}"
        any_ok = False
        for ch in channels:
            try:
                await send_via_channel(ch, subject=subject, body=message)
                await _alert_logs.insert(
                    policy_id=policy.id,
                    channel_id=ch.id,
                    status="sent",
                    message=message,
                )
                any_ok = True
            except Exception as exc:  # noqa: BLE001
                log.exception("notify policy=%s channel=%s failed", policy.id, ch.id)
                await _alert_logs.insert(
                    policy_id=policy.id,
                    channel_id=ch.id,
                    status="failed",
                    message=message,
                    detail=str(exc),
                )
        return any_ok


async def latest_dispatch_status_by_policy(
    db: AsyncSession,
    policy_ids: list[int],
) -> dict[int, str]:
    return await _alert_logs.latest_status_by_policy(policy_ids)


async def run_alert_policies(db: AsyncSession) -> int:
    return await AlertPolicyEvaluator().run(db)
