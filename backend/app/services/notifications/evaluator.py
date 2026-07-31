"""Evaluate alert policies and dispatch notifications."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.alert_conditions import CONDITION_TYPE_MAP
from app.constants.alert_site_scope import (
    SITE_SCOPE_ALL,
    SITE_SCOPE_ANY,
    SITE_SCOPE_SINGLE,
    parse_site_scope,
    site_scope_label,
)
from app.core.redis import get_redis
from app.models.notification import AlertPolicy, NotificationChannel
from app.services.analytics.alert_log_store import AlertLogStore
from app.services.notifications.channels import send_via_channel
from app.services.notifications.email_templates import build_alert_email
from app.services.traffic_intel.constants import REDIS_SNAPSHOT_KEY
from app.services.traffic_intel.detector import AnomalyDetector
from app.services.traffic_intel.store.baseline_mysql import BaselineStore
from app.services.traffic_intel.store.clickhouse import ClickHouseTrafficStore
from app.services.traffic_intel.timezone import get_traffic_timezone
from app.services.traffic_intel.types import TrafficIntelConfig
from app.services.traffic_intel.windows import is_baseline_stable

log = logging.getLogger("waf.notify.evaluator")

TRAFFIC_SNAPSHOT_KEY = REDIS_SNAPSHOT_KEY
_alert_logs = AlertLogStore()


@dataclass(frozen=True)
class EvalHit:
    message: str
    matched_site_id: int | None = None


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
        hit = await self.evaluate_hit(policy, db)
        return hit.message if hit else None

    async def evaluate_hit(self, policy: AlertPolicy, db: AsyncSession) -> EvalHit | None:
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
        if ctype == "traffic.origin_abs_gt":
            return await self._traffic_abs(params, direction="gt", label=label, origin=True)
        if ctype == "traffic.origin_abs_lt":
            return await self._traffic_abs(params, direction="lt", label=label, origin=True)
        if ctype == "traffic.origin_qps_gt":
            return await self._traffic_qps(params, direction="gt", label=label, origin=True)
        if ctype == "traffic.origin_qps_lt":
            return await self._traffic_qps(params, direction="lt", label=label, origin=True)
        if ctype == "traffic.burst_logging":
            return await self._traffic_burst(label)
        if ctype == "security.block_count":
            return await self._block_count(params, label)
        if ctype == "security.block_rate":
            return await self._block_rate(params, label)
        if ctype.startswith("system."):
            return await self._system_metric(ctype, params, label)
        return None

    async def _traffic_baseline(
        self,
        policy: AlertPolicy,
        db: AsyncSession,
        params: dict,
        *,
        direction: str,
    ) -> EvalHit | None:
        window_sec = int(params.get("window_sec", 300))
        percent = float(params.get("percent", 50))
        scope, site_id = parse_site_scope(params)
        timezone_name = await get_traffic_timezone(db)

        if scope == SITE_SCOPE_ANY:
            snapshot = await self._load_snapshot()
            if not snapshot:
                return None
            for sid_str in sorted((snapshot.get("sites") or {}).keys(), key=lambda x: int(x)):
                sid = int(sid_str)
                hit = await self._traffic_baseline_for_site(
                    policy,
                    db,
                    window_sec=window_sec,
                    percent=percent,
                    site_id=sid,
                    direction=direction,
                    timezone_name=timezone_name,
                )
                if hit:
                    return hit
            return None

        baseline = await self._baselines.get(
            db,
            site_id=site_id if scope == SITE_SCOPE_SINGLE else None,
            window_sec=window_sec,
            as_of=datetime.utcnow(),
            timezone_name=timezone_name,
        )
        if not baseline or baseline.avg_requests <= 0:
            return None
        if not is_baseline_stable(window_sec, baseline.sample_count):
            return None
        current = await self._window_requests(window_sec, site_id=site_id, scope=scope)
        if direction == "gt":
            cfg = TrafficIntelConfig(spike_ratio=percent / 100)
            anomaly = self._detector._compare(  # noqa: SLF001
                current, baseline, cfg, datetime.utcnow()
            )
            if anomaly is None:
                return None
            return EvalHit(message=f"【{policy.name}】{anomaly.message}", matched_site_id=site_id)
        threshold = baseline.avg_requests * (1 - percent / 100)
        if current >= threshold:
            return None
        scope_label = site_scope_label(scope, site_id)
        return EvalHit(
            message=(
                f"【{policy.name}】{scope_label} {window_sec}s 窗口内当前 {current} 次请求，"
                f"低于基线 {baseline.avg_requests:.0f} 的 {percent:.0f}%"
            ),
            matched_site_id=site_id,
        )

    async def _traffic_baseline_for_site(
        self,
        policy: AlertPolicy,
        db: AsyncSession,
        *,
        window_sec: int,
        percent: float,
        site_id: int,
        direction: str,
        timezone_name: str,
    ) -> EvalHit | None:
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
        current = await self._window_requests(
            window_sec,
            site_id=site_id,
            scope=SITE_SCOPE_SINGLE,
        )
        if direction == "gt":
            cfg = TrafficIntelConfig(spike_ratio=percent / 100)
            anomaly = self._detector._compare(  # noqa: SLF001
                current, baseline, cfg, datetime.utcnow()
            )
            if anomaly is None:
                return None
            return EvalHit(
                message=f"【{policy.name}】站点 #{site_id} {anomaly.message}",
                matched_site_id=site_id,
            )
        threshold = baseline.avg_requests * (1 - percent / 100)
        if current >= threshold:
            return None
        return EvalHit(
            message=(
                f"【{policy.name}】站点 #{site_id} {window_sec}s 窗口内当前 {current} 次请求，"
                f"低于基线 {baseline.avg_requests:.0f} 的 {percent:.0f}%"
            ),
            matched_site_id=site_id,
        )

    async def _traffic_abs(
        self,
        params: dict,
        *,
        direction: str,
        label: str,
        origin: bool = False,
    ) -> EvalHit | None:
        window_sec = int(params.get("window_sec", 300))
        threshold = int(params.get("threshold", 0))
        scope, site_id = parse_site_scope(params)
        metric = "回源请求" if origin else "请求"

        if scope == SITE_SCOPE_ANY:
            snapshot = await self._load_snapshot()
            if not snapshot:
                return None
            for sid_str in sorted((snapshot.get("sites") or {}).keys(), key=lambda x: int(x)):
                sid = int(sid_str)
                current = self._requests_from_site_data(snapshot, sid, window_sec, origin=origin)
                if direction == "gt" and current > threshold:
                    return EvalHit(
                        message=(
                            f"【预警】{label}：站点 #{sid} {window_sec}s 窗口内 {current} 次{metric}，"
                            f"高于阈值 {threshold}"
                        ),
                        matched_site_id=sid,
                    )
                if direction == "lt" and current < threshold:
                    return EvalHit(
                        message=(
                            f"【预警】{label}：站点 #{sid} {window_sec}s 窗口内 {current} 次{metric}，"
                            f"低于阈值 {threshold}"
                        ),
                        matched_site_id=sid,
                    )
            return None

        current = await self._window_requests(
            window_sec,
            site_id=site_id,
            scope=scope,
            origin=origin,
        )
        scope_label = site_scope_label(scope, site_id)
        if direction == "gt" and current > threshold:
            return EvalHit(
                message=(
                    f"【预警】{label}：{scope_label} {window_sec}s 窗口内 {current} 次{metric}，"
                    f"高于阈值 {threshold}"
                ),
                matched_site_id=site_id,
            )
        if direction == "lt" and current < threshold:
            return EvalHit(
                message=(
                    f"【预警】{label}：{scope_label} {window_sec}s 窗口内 {current} 次{metric}，"
                    f"低于阈值 {threshold}"
                ),
                matched_site_id=site_id,
            )
        return None

    async def _traffic_qps(
        self,
        params: dict,
        *,
        direction: str,
        label: str,
        origin: bool = False,
    ) -> EvalHit | None:
        window_sec = int(params.get("window_sec", 300))
        threshold = float(params.get("threshold", 0))
        scope, site_id = parse_site_scope(params)
        metric = "回源 QPS" if origin else "QPS"

        if scope == SITE_SCOPE_ANY:
            snapshot = await self._load_snapshot()
            if not snapshot:
                return None
            for sid_str in sorted((snapshot.get("sites") or {}).keys(), key=lambda x: int(x)):
                sid = int(sid_str)
                current = self._requests_from_site_data(snapshot, sid, window_sec, origin=origin)
                qps = current / window_sec if window_sec > 0 else 0
                if direction == "gt" and qps > threshold:
                    return EvalHit(
                        message=(
                            f"【预警】{label}：站点 #{sid} {window_sec}s 窗口平均 {metric} {qps:.2f}，"
                            f"高于阈值 {threshold}"
                        ),
                        matched_site_id=sid,
                    )
                if direction == "lt" and qps < threshold:
                    return EvalHit(
                        message=(
                            f"【预警】{label}：站点 #{sid} {window_sec}s 窗口平均 {metric} {qps:.2f}，"
                            f"低于阈值 {threshold}"
                        ),
                        matched_site_id=sid,
                    )
            return None

        current = await self._window_requests(
            window_sec,
            site_id=site_id,
            scope=scope,
            origin=origin,
        )
        qps = current / window_sec if window_sec > 0 else 0
        scope_label = site_scope_label(scope, site_id)
        if direction == "gt" and qps > threshold:
            return EvalHit(
                message=(
                    f"【预警】{label}：{scope_label} {window_sec}s 窗口平均 {metric} {qps:.2f}，"
                    f"高于阈值 {threshold}"
                ),
                matched_site_id=site_id,
            )
        if direction == "lt" and qps < threshold:
            return EvalHit(
                message=(
                    f"【预警】{label}：{scope_label} {window_sec}s 窗口平均 {metric} {qps:.2f}，"
                    f"低于阈值 {threshold}"
                ),
                matched_site_id=site_id,
            )
        return None

    async def _traffic_burst(self, label: str) -> EvalHit | None:
        redis = get_redis()
        raw = await redis.get(TRAFFIC_SNAPSHOT_KEY)
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        if data.get("global", {}).get("burst_active"):
            return EvalHit(
                message=f"【预警】{label}：系统已进入流量自动取证模式，建议关注攻击日志。"
            )
        return None

    async def _block_count(self, params: dict, label: str) -> EvalHit | None:
        window_min = int(params.get("window_min", 5))
        threshold = int(params.get("threshold", 100))
        scope, site_id = parse_site_scope(params)

        if scope == SITE_SCOPE_ANY:
            for sid, blocked in sorted(
                (await self._query_block_stats_by_site(window_min)).items(),
                key=lambda item: item[0],
            ):
                if blocked > threshold:
                    return EvalHit(
                        message=(
                            f"【预警】{label}：站点 #{sid} 近 {window_min} 分钟拦截 {blocked} 次，"
                            f"超过阈值 {threshold}"
                        ),
                        matched_site_id=sid,
                    )
            return None

        count = await self._query_log_count(window_min, site_id=site_id, scope=scope, blocked_only=True)
        if count > threshold:
            scope_label = site_scope_label(scope, site_id)
            return EvalHit(
                message=(
                    f"【预警】{label}：{scope_label} 近 {window_min} 分钟拦截 {count} 次，"
                    f"超过阈值 {threshold}"
                ),
                matched_site_id=site_id,
            )
        return None

    async def _block_rate(self, params: dict, label: str) -> EvalHit | None:
        window_min = int(params.get("window_min", 5))
        percent = float(params.get("percent", 30))
        scope, site_id = parse_site_scope(params)

        if scope == SITE_SCOPE_ANY:
            for sid, (total, blocked) in sorted(
                (await self._query_block_stats_by_site(window_min, with_total=True)).items(),
                key=lambda item: item[0],
            ):
                if total <= 0:
                    continue
                rate = blocked / total * 100
                if rate > percent:
                    return EvalHit(
                        message=(
                            f"【预警】{label}：站点 #{sid} 近 {window_min} 分钟拦截率 {rate:.1f}%，"
                            f"超过阈值 {percent:.0f}%（{blocked}/{total}）"
                        ),
                        matched_site_id=sid,
                    )
            return None

        total, blocked = await self._query_block_stats(window_min, site_id=site_id, scope=scope)
        if total <= 0:
            return None
        rate = blocked / total * 100
        if rate > percent:
            scope_label = site_scope_label(scope, site_id)
            return EvalHit(
                message=(
                    f"【预警】{label}：{scope_label} 近 {window_min} 分钟拦截率 {rate:.1f}%，"
                    f"超过阈值 {percent:.0f}%（{blocked}/{total}）"
                ),
                matched_site_id=site_id,
            )
        return None

    async def _system_metric(self, ctype: str, params: dict, label: str) -> EvalHit | None:
        from app.services.system_metrics import read_system_metrics_snapshot, window_metric_value

        window_sec = int(params.get("window_sec", 300))
        threshold = float(params.get("threshold", 0))
        metric_map = {
            "system.container_cpu_gt": ("container_cpu_pct", "容器 CPU", "%"),
            "system.host_cpu_gt": ("host_cpu_pct", "宿主机 CPU", "%"),
        }
        meta = metric_map.get(ctype)
        if not meta:
            return None
        metric_key, metric_label, unit = meta
        snapshot = await read_system_metrics_snapshot()
        current = window_metric_value(snapshot, window_sec=window_sec, metric=metric_key)
        if current is None:
            return None
        if current <= threshold:
            return None
        unit_text = unit or ""
        return EvalHit(
            message=(
                f"【预警】{label}：近 {window_sec}s 平均{metric_label} {current:.2f}{unit_text}，"
                f"高于阈值 {threshold:g}{unit_text}"
            )
        )

    async def _load_snapshot(self) -> dict | None:
        redis = get_redis()
        raw = await redis.get(TRAFFIC_SNAPSHOT_KEY)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def _requests_from_site_data(
        self,
        data: dict,
        site_id: int,
        window_sec: int,
        *,
        origin: bool = False,
    ) -> int:
        window_key = "origin_windows" if origin else "windows"
        windows = (data.get("sites") or {}).get(str(site_id), {}).get(window_key) or []
        for w in windows:
            try:
                if int(w.get("sec", 0)) == window_sec:
                    return int(w.get("requests") or 0)
            except (TypeError, ValueError):
                continue
        return 0

    async def _window_requests(
        self,
        window_sec: int,
        *,
        site_id: int | None,
        scope: str = SITE_SCOPE_ALL,
        origin: bool = False,
    ) -> int:
        if scope == SITE_SCOPE_SINGLE:
            effective_site_id = site_id
        else:
            effective_site_id = None
        return await self._snapshot_window_requests(
            window_sec,
            site_id=effective_site_id,
            origin=origin,
        )

    async def _snapshot_window_requests(
        self,
        window_sec: int,
        *,
        site_id: int | None = None,
        origin: bool = False,
    ) -> int:
        redis = get_redis()
        raw = await redis.get(TRAFFIC_SNAPSHOT_KEY)
        if not raw:
            return 0
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return 0
        window_key = "origin_windows" if origin else "windows"
        if site_id is None:
            windows = data.get("global", {}).get(window_key) or []
        else:
            windows = (data.get("sites") or {}).get(str(site_id), {}).get(window_key) or []
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
        scope: str = SITE_SCOPE_ALL,
        blocked_only: bool,
    ) -> int:
        total, blocked = await self._query_block_stats(
            window_min,
            site_id=site_id,
            scope=scope,
        )
        return blocked if blocked_only else total

    async def _query_block_stats(
        self,
        window_min: int,
        *,
        site_id: int | None,
        scope: str = SITE_SCOPE_ALL,
    ) -> tuple[int, int]:
        def _query() -> tuple[int, int]:
            from app.core.clickhouse import get_clickhouse

            clauses = ["ts >= now() - INTERVAL {mins:UInt16} MINUTE"]
            params: dict = {"mins": window_min}
            if scope == SITE_SCOPE_SINGLE and site_id is not None:
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

    async def _query_block_stats_by_site(
        self,
        window_min: int,
        *,
        with_total: bool = False,
    ) -> dict[int, int] | dict[int, tuple[int, int]]:
        def _query() -> dict[int, tuple[int, int]]:
            from app.core.clickhouse import get_clickhouse

            client = get_clickhouse()
            rows = client.query(
                """
                SELECT site_id, count(), countIf(blocked = 1)
                FROM waf_logs
                WHERE ts >= now() - INTERVAL {mins:UInt16} MINUTE
                GROUP BY site_id
                """,
                parameters={"mins": window_min},
            ).result_rows
            out: dict[int, tuple[int, int]] = {}
            for row in rows or []:
                out[int(row[0])] = (int(row[1]), int(row[2]))
            return out

        stats = await asyncio.to_thread(_query)
        if with_total:
            return stats
        return {sid: blocked for sid, (_total, blocked) in stats.items()}

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
        traffic_overview = None
        try:
            from app.services.ai_guard.defense.traffic_context import build_defense_traffic_overview

            params = policy.condition_params or {}
            focus_site_id = params.get("site_id")
            try:
                focus_site_id = int(focus_site_id) if focus_site_id not in (None, "") else None
            except (TypeError, ValueError):
                focus_site_id = None
            if params.get("site_scope") == SITE_SCOPE_ANY:
                focus_site_id = None
            focus_window_sec = params.get("window_sec")
            try:
                focus_window_sec = int(focus_window_sec) if focus_window_sec not in (None, "") else None
            except (TypeError, ValueError):
                focus_window_sec = None
            log_window_min = params.get("window_min")
            try:
                log_window_min = int(log_window_min) if log_window_min not in (None, "") else 30
            except (TypeError, ValueError):
                log_window_min = 30
            traffic_overview = await build_defense_traffic_overview(
                db,
                focus_site_id=focus_site_id,
                focus_window_sec=focus_window_sec,
                log_window_min=max(log_window_min, 5),
            )
        except Exception:  # noqa: BLE001
            log.exception("alert email traffic overview failed policy=%s", policy.id)

        system_metrics = None
        try:
            from app.services.system_metrics import read_system_metrics_snapshot

            system_metrics = await read_system_metrics_snapshot()
        except Exception:  # noqa: BLE001
            log.exception("alert email system metrics failed policy=%s", policy.id)

        plain, html_body = build_alert_email(
            policy_name=policy.name,
            message=message,
            traffic_overview=traffic_overview,
            system_metrics=system_metrics,
        )
        any_ok = False
        for ch in channels:
            try:
                await send_via_channel(
                    ch, subject=subject, body=plain, html_body=html_body
                )
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
