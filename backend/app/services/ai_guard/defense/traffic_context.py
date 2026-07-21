"""Build per-site traffic fundamentals for AI defense prompts."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.traffic_windows import TRAFFIC_WINDOW_LABELS, TRAFFIC_WINDOWS_SEC
from app.core.redis import get_redis
from app.models import Site
from app.services.site_domains import site_domain_list
from app.services.traffic_intel.constants import REDIS_SNAPSHOT_KEY
from app.services.traffic_intel.ingest import parse_snapshot
from app.services.traffic_intel.types import TrafficSnapshot, WindowSample

log = logging.getLogger("waf.ai_guard.traffic_context")

# Prefer these windows in the prompt when the trigger does not specify one.
_PRIMARY_WINDOWS = (60, 300, 1800)
_MAX_SITES_IN_OVERVIEW = 30


def _window_rows(samples: list[WindowSample]) -> list[dict[str, Any]]:
    by_sec = {int(s.window_sec): s for s in samples}
    rows: list[dict[str, Any]] = []
    for sec in TRAFFIC_WINDOWS_SEC:
        sample = by_sec.get(sec)
        if sample is None:
            continue
        requests = int(sample.requests or 0)
        qps = float(sample.qps or 0.0)
        if qps <= 0 and sec > 0:
            qps = requests / sec
        rows.append({
            "window_sec": sec,
            "label": TRAFFIC_WINDOW_LABELS.get(sec, f"{sec} 秒"),
            "requests": requests,
            "qps": round(qps, 3),
        })
    return rows


def _pick_primary_requests(windows: list[dict[str, Any]], focus_window_sec: int | None) -> int:
    if focus_window_sec:
        for row in windows:
            if row["window_sec"] == focus_window_sec:
                return int(row["requests"])
    for sec in _PRIMARY_WINDOWS:
        for row in windows:
            if row["window_sec"] == sec:
                return int(row["requests"])
    return int(windows[0]["requests"]) if windows else 0


async def _load_site_meta(db: AsyncSession) -> dict[int, dict[str, Any]]:
    rows = (await db.execute(select(Site).order_by(Site.id.asc()))).scalars().all()
    return {
        int(s.id): {
            "site_id": int(s.id),
            "name": s.name,
            "domain": s.domain,
            "domains": site_domain_list(s),
            "enabled": bool(s.enabled),
        }
        for s in rows
    }


async def _recent_log_stats_by_site(window_min: int) -> dict[str, Any]:
    """Aggregate recent waf_logs totals / blocks globally and per site."""

    def _query() -> dict[str, Any]:
        from app.core.clickhouse import get_clickhouse

        client = get_clickhouse()
        mins = max(1, int(window_min))
        global_row = client.query(
            "SELECT count(), countIf(blocked = 1) FROM waf_logs "
            "WHERE ts >= now() - INTERVAL {mins:UInt16} MINUTE",
            parameters={"mins": mins},
        ).result_rows
        total = int(global_row[0][0]) if global_row else 0
        blocked = int(global_row[0][1]) if global_row else 0

        site_rows = client.query(
            "SELECT site_id, count(), countIf(blocked = 1) FROM waf_logs "
            "WHERE ts >= now() - INTERVAL {mins:UInt16} MINUTE "
            "AND site_id IS NOT NULL "
            "GROUP BY site_id "
            "ORDER BY count() DESC "
            "LIMIT {lim:UInt32}",
            parameters={"mins": mins, "lim": _MAX_SITES_IN_OVERVIEW},
        ).result_rows

        by_site = []
        for site_id, cnt, blk in site_rows:
            cnt_i = int(cnt)
            blk_i = int(blk)
            by_site.append({
                "site_id": int(site_id),
                "total": cnt_i,
                "blocked": blk_i,
                "passed": max(0, cnt_i - blk_i),
                "block_rate_pct": round((blk_i / cnt_i * 100) if cnt_i else 0.0, 2),
            })

        return {
            "window_min": mins,
            "global": {
                "total": total,
                "blocked": blocked,
                "passed": max(0, total - blocked),
                "block_rate_pct": round((blocked / total * 100) if total else 0.0, 2),
            },
            "by_site": by_site,
        }

    try:
        return await asyncio.to_thread(_query)
    except Exception:  # noqa: BLE001
        log.exception("failed to load recent log stats for defense traffic overview")
        return {
            "window_min": max(1, int(window_min)),
            "global": {"total": 0, "blocked": 0, "passed": 0, "block_rate_pct": 0.0},
            "by_site": [],
            "error": "clickhouse_unavailable",
        }


async def build_defense_traffic_overview(
    db: AsyncSession,
    *,
    focus_site_id: int | None = None,
    focus_window_sec: int | None = None,
    log_window_min: int = 30,
) -> dict[str, Any]:
    """Collect global + per-site request/QPS fundamentals for defense analysis."""
    site_meta = await _load_site_meta(db)
    snapshot: TrafficSnapshot | None = None
    try:
        raw = await get_redis().get(REDIS_SNAPSHOT_KEY)
        if raw:
            snapshot = parse_snapshot(raw)
    except Exception:  # noqa: BLE001
        log.exception("failed to read traffic snapshot for defense overview")

    global_windows = _window_rows(snapshot.global_windows if snapshot else [])
    site_entries: list[dict[str, Any]] = []

    snap_sites = snapshot.site_windows if snapshot else {}
    site_ids = set(snap_sites.keys()) | set(site_meta.keys())
    if focus_site_id is not None:
        site_ids.add(int(focus_site_id))

    for site_id in site_ids:
        meta = site_meta.get(int(site_id), {
            "site_id": int(site_id),
            "name": f"站点 #{site_id}",
            "domain": None,
            "domains": [],
            "enabled": None,
        })
        windows = _window_rows(snap_sites.get(int(site_id), []))
        if not windows and int(site_id) not in snap_sites and focus_site_id != int(site_id):
            # Skip idle configured sites that have no live counters, unless focused.
            continue
        site_entries.append({
            **meta,
            "windows": windows,
            "_sort_requests": _pick_primary_requests(windows, focus_window_sec),
        })

    site_entries.sort(key=lambda item: (-int(item["_sort_requests"]), int(item["site_id"])))

    trimmed: list[dict[str, Any]] = []
    seen: set[int] = set()
    for item in site_entries:
        if len(trimmed) >= _MAX_SITES_IN_OVERVIEW:
            break
        sid = int(item["site_id"])
        seen.add(sid)
        trimmed.append({k: v for k, v in item.items() if k != "_sort_requests"})

    if focus_site_id is not None and int(focus_site_id) not in seen:
        meta = site_meta.get(int(focus_site_id), {
            "site_id": int(focus_site_id),
            "name": f"站点 #{focus_site_id}",
            "domain": None,
            "domains": [],
            "enabled": None,
        })
        trimmed.insert(0, {
            **meta,
            "windows": _window_rows(snap_sites.get(int(focus_site_id), [])),
        })

    recent_logs = await _recent_log_stats_by_site(log_window_min)
    # Attach site names onto log breakdown.
    named_log_sites = []
    for row in recent_logs.get("by_site") or []:
        meta = site_meta.get(int(row["site_id"]))
        named_log_sites.append({
            **row,
            "name": (meta or {}).get("name") or f"站点 #{row['site_id']}",
            "domains": (meta or {}).get("domains") or [],
        })
    recent_logs["by_site"] = named_log_sites

    return {
        "source": "engine_redis_snapshot+clickhouse_logs",
        "updated_at": snapshot.updated_at if snapshot else None,
        "burst_active": bool(snapshot.burst_active) if snapshot else False,
        "focus": {
            "site_id": focus_site_id,
            "window_sec": focus_window_sec,
        },
        "global": {
            "windows": global_windows,
        },
        "sites": trimmed,
        "site_count_with_traffic": len(trimmed),
        "recent_log_stats": recent_logs,
        "notes": [
            "windows 来自引擎实时计数：含各时间窗口的 requests 与平均 QPS",
            "sites 按焦点窗口（或 1/5/30 分钟）请求量降序，便于判断流量集中在哪些站点",
            "recent_log_stats 为近期防护日志总量/拦截量的分站点统计",
        ],
    }
