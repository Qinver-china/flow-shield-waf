import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.redis import get_redis
from app.models import Certificate, Exception_, IpList, RateLimit, Rule, Site, User
from app.services.analytics.alert_log_store import AlertLogStore
from app.services.analytics.incident_store import IncidentStore
from app.schemas.common import ok
from app.schemas.dashboard import (
    DashboardFeedItemOut,
    DashboardFeedOut,
    DashboardHealthOut,
    DashboardSummaryOut,
    RuleSyncHealthOut,
)
from app.services.logging.query_clickhouse import stats_overview
from app.services.rule_sync import VERSION_KEY

router = APIRouter()
log = logging.getLogger("waf.dashboard")


async def _count_enabled(db: AsyncSession, model, extra=None) -> dict[str, int]:
    total_q = select(func.count(model.id))
    enabled_q = select(func.count(model.id)).where(model.enabled.is_(True))
    if extra is not None:
        total_q = total_q.where(extra)
        enabled_q = enabled_q.where(extra)
    total = (await db.execute(total_q)).scalar_one()
    enabled = (await db.execute(enabled_q)).scalar_one()
    return {"total": int(total), "enabled": int(enabled)}


def _delta_pct(current: int, previous: int) -> float | None:
    if previous <= 0:
        return None if current <= 0 else 100.0
    return round(((current - previous) / previous) * 100, 2)


@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    sites = await _count_enabled(db, Site)
    rules = await _count_enabled(db, Rule)
    blacklist = await _count_enabled(
        db, IpList, IpList.list_type == "black"
    )
    whitelist = await _count_enabled(
        db, IpList, IpList.list_type == "white"
    )
    exceptions = await _count_enabled(db, Exception_)
    ratelimits = await _count_enabled(db, RateLimit)
    certificates = (
        await db.execute(select(func.count(Certificate.id)))
    ).scalar_one()
    log_stats = await stats_overview(hours=24)
    return ok({
        "counts": {
            "sites": sites,
            "rules": rules,
            "blacklist": blacklist,
            "whitelist": whitelist,
            "exceptions": exceptions,
            "ratelimits": ratelimits,
            "certificates": {"total": int(certificates)},
        },
        "last_24h": log_stats,
    })


@router.get("/health")
async def health(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    database_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        database_status = "error"

    redis_status = "ok"
    rule_sync = RuleSyncHealthOut(status="ok")
    try:
        redis = get_redis()
        await redis.ping()
        version_raw = await redis.get(VERSION_KEY)
        if version_raw is not None:
            rule_sync.version = int(version_raw)
        else:
            rule_sync.status = "stale"
    except Exception:  # noqa: BLE001
        redis_status = "error"
        rule_sync.status = "error"

    clickhouse_status = "ok"
    try:
        from app.core.clickhouse import get_clickhouse

        get_clickhouse().query("SELECT 1")
    except Exception:  # noqa: BLE001
        clickhouse_status = "error"

    return ok(
        DashboardHealthOut(
            database=database_status,
            redis=redis_status,
            clickhouse=clickhouse_status,
            rule_sync=rule_sync,
        ).model_dump()
    )


@router.get("/system-metrics")
async def system_metrics(_user: User = Depends(get_current_user)):
    """CPU window averages for the dashboard card (shortest window is primary)."""
    from app.constants.system_metrics import (
        SYSTEM_METRIC_WINDOW_LABELS,
        SYSTEM_METRIC_WINDOWS_SEC,
    )
    from app.services.system_metrics import read_system_metrics_snapshot, window_metric_value

    primary_sec = int(SYSTEM_METRIC_WINDOWS_SEC[0])
    snapshot = await read_system_metrics_snapshot()
    instant = (snapshot or {}).get("instant") or {}

    windows_out: list[dict] = []
    for sec in SYSTEM_METRIC_WINDOWS_SEC:
        win_row = ((snapshot or {}).get("windows") or {}).get(str(sec)) or {}
        windows_out.append({
            "sec": int(sec),
            "label": SYSTEM_METRIC_WINDOW_LABELS.get(sec, f"{sec} 秒"),
            "container_cpu_pct": window_metric_value(
                snapshot, window_sec=int(sec), metric="container_cpu_pct"
            ),
            "host_cpu_pct": window_metric_value(
                snapshot, window_sec=int(sec), metric="host_cpu_pct"
            ),
            "samples": win_row.get("samples"),
            "ready": win_row.get("ready"),
        })

    primary = next((w for w in windows_out if w["sec"] == primary_sec), None) or {}
    return ok({
        "window_sec": primary_sec,
        "window_label": SYSTEM_METRIC_WINDOW_LABELS.get(primary_sec, f"{primary_sec} 秒"),
        "container_cpu_pct": primary.get("container_cpu_pct"),
        "host_cpu_pct": primary.get("host_cpu_pct"),
        "windows": windows_out,
        "cpu_cores": instant.get("cpu_cores"),
        "source": instant.get("source"),
        "updated_at": (snapshot or {}).get("updated_at"),
        "available": bool(snapshot) and any(
            w.get("container_cpu_pct") is not None or w.get("host_cpu_pct") is not None
            for w in windows_out
        ),
    })


@router.get("/summary")
async def summary(_user: User = Depends(get_current_user)):
    now = datetime.utcnow()
    current_end = now
    current_start = now - timedelta(hours=24)
    previous_end = current_start
    previous_start = now - timedelta(hours=48)

    current = await stats_overview(hours=24, start=current_start, end=current_end)
    previous = await stats_overview(hours=24, start=previous_start, end=previous_end)

    return ok(
        DashboardSummaryOut(
            blocked_delta_pct=_delta_pct(current["blocked"], previous["blocked"]),
            passed_delta_pct=_delta_pct(current["passed"], previous["passed"]),
            total_requests_delta_pct=_delta_pct(current["total"], previous["total"]),
            unique_ips_delta_pct=_delta_pct(
                current["unique_ips"], previous["unique_ips"]
            ),
            current={
                "total": current["total"],
                "blocked": current["blocked"],
                "passed": current["passed"],
                "unique_ips": current["unique_ips"],
            },
            previous={
                "total": previous["total"],
                "blocked": previous["blocked"],
                "passed": previous["passed"],
                "unique_ips": previous["unique_ips"],
            },
        ).model_dump()
    )


@router.get("/feed")
async def feed(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    items: list[DashboardFeedItemOut] = []

    alert_rows = await AlertLogStore().list_recent(limit=limit)
    for row in alert_rows:
        items.append(
            DashboardFeedItemOut(
                id=f"alert-{row.id}",
                type="alert",
                title=row.message or "预警通知",
                detail=row.detail if isinstance(row.detail, str) else (
                    str(row.detail) if row.detail is not None else None
                ),
                severity="warning" if row.status != "sent" else "info",
                created_at=row.created_at,
            )
        )

    try:
        from app.core.clickhouse import get_clickhouse

        client = get_clickhouse()
        since = datetime.utcnow() - timedelta(hours=24)

        # Observe hits are logged with blocked=0; still exclude them explicitly.
        # Feed only surfaces terminal protection actions.
        _FEED_ACTIONS = ("block", "js_challenge", "captcha", "slide_captcha")
        _FEED_SEVERITY = {
            "block": "danger",
            "js_challenge": "info",
            "captcha": "warning",
            "slide_captcha": "info",
        }

        def _query_logs():
            return client.query(
                "SELECT ts, client_ip, domain, rule_name, action FROM waf_logs "
                "WHERE blocked = 1 "
                "AND action IN {actions:Array(String)} "
                "AND ts >= {start:DateTime} "
                "ORDER BY ts DESC LIMIT {lim:UInt32}",
                parameters={
                    "start": since,
                    "lim": min(limit, 20),
                    "actions": list(_FEED_ACTIONS),
                },
            ).result_rows

        log_rows = await asyncio.wait_for(asyncio.to_thread(_query_logs), timeout=10)
        for ts, client_ip, domain, rule_name, action in log_rows:
            mode = (action or "block").strip() or "block"
            if mode not in _FEED_ACTIONS:
                continue
            site_label = (domain or "").strip() or None
            rule_label = (rule_name or "").strip() or None
            items.append(
                DashboardFeedItemOut(
                    id=f"log-{ts}-{client_ip}",
                    type=mode,
                    title=(client_ip or "").strip() or "未知 IP",
                    detail=None,
                    site=site_label,
                    rule=rule_label,
                    severity=_FEED_SEVERITY.get(mode, "danger"),
                    created_at=ts if isinstance(ts, datetime) else datetime.utcnow(),
                )
            )
    except Exception:  # noqa: BLE001
        pass

    pending_ai = 0
    try:
        from app.services.ai_guard.defense.pipeline import expire_stale_suggested_incidents

        await expire_stale_suggested_incidents()
        pending_ai = await IncidentStore().count_by_status(["suggested", "pending"])
    except Exception:  # noqa: BLE001
        log.exception("dashboard feed: pending AI incident count failed")

    items.sort(key=lambda x: x.created_at, reverse=True)
    return ok(
        DashboardFeedOut(
            items=items[:limit],
            pending_ai_incidents=int(pending_ai or 0),
        ).model_dump()
    )
