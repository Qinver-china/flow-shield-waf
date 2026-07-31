import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.constants.logging_settings import DEFAULT_AUTO_THRESHOLDS
from app.core.db import get_db
from app.core.redis import get_redis
from app.models import User
from app.schemas.common import ok
from app.services import waf_settings

router = APIRouter()

SNAPSHOT_KEY = "waf:traffic:snapshot"


def _default_windows(thresholds: dict[int, int]) -> list[dict]:
    windows = []
    for t in DEFAULT_AUTO_THRESHOLDS:
        sec = int(t["window_sec"])
        windows.append({
            "sec": sec,
            "requests": 0,
            "qps": 0.0,
            "origin_requests": 0,
            "origin_qps": 0.0,
            "threshold": thresholds.get(sec, int(t["max_requests"])),
        })
    return windows


def _origin_by_sec(windows: list[dict] | None) -> dict[int, int]:
    out: dict[int, int] = {}
    for w in windows or []:
        try:
            sec = int(w.get("sec", 0))
            req = int(w.get("requests") or 0)
        except (TypeError, ValueError):
            continue
        if sec > 0:
            out[sec] = req
    return out


def _window_row(
    sec: int,
    requests: int,
    thresholds: dict[int, int],
    *,
    threshold=None,
    origin_requests: int = 0,
) -> dict:
    sec = int(sec)
    requests = int(requests or 0)
    origin_requests = int(origin_requests or 0)
    return {
        "sec": sec,
        "requests": requests,
        # Always derive QPS from the requests being returned (never trust a stale field).
        "qps": (requests / sec) if sec > 0 else 0.0,
        "origin_requests": origin_requests,
        "origin_qps": (origin_requests / sec) if sec > 0 else 0.0,
        "threshold": threshold if threshold is not None else thresholds.get(sec),
    }


def _windows_from_snapshot(
    snapshot_windows: list[dict],
    thresholds: dict[int, int],
    *,
    origin_windows: list[dict] | None = None,
) -> list[dict]:
    origin_by_sec = _origin_by_sec(origin_windows)
    out: list[dict] = []
    for w in snapshot_windows:
        try:
            sec = int(w.get("sec", 0))
        except (TypeError, ValueError):
            continue
        if sec <= 0:
            continue
        try:
            requests = int(w.get("requests") or 0)
        except (TypeError, ValueError):
            requests = 0
        thr = w.get("threshold")
        out.append(
            _window_row(
                sec,
                requests,
                thresholds,
                threshold=thr,
                origin_requests=origin_by_sec.get(sec, 0),
            )
        )
    return out


def _windows_sum_sites(
    sites: dict,
    thresholds: dict[int, int],
    *,
    fallback_global: list[dict] | None = None,
    fallback_origin_global: list[dict] | None = None,
) -> list[dict]:
    """Build all-sites windows by summing per-site requests, then recompute QPS."""
    by_sec: dict[int, int] = {}
    origin_by_sec: dict[int, int] = {}
    order: list[int] = []
    for site_data in (sites or {}).values():
        for w in (site_data or {}).get("windows") or []:
            try:
                sec = int(w.get("sec", 0))
                req = int(w.get("requests") or 0)
            except (TypeError, ValueError):
                continue
            if sec <= 0:
                continue
            if sec not in by_sec:
                order.append(sec)
                by_sec[sec] = 0
            by_sec[sec] += req
        for w in (site_data or {}).get("origin_windows") or []:
            try:
                sec = int(w.get("sec", 0))
                req = int(w.get("requests") or 0)
            except (TypeError, ValueError):
                continue
            if sec <= 0:
                continue
            origin_by_sec[sec] = origin_by_sec.get(sec, 0) + req
            if sec not in by_sec:
                order.append(sec)
                by_sec.setdefault(sec, 0)

    if not order and fallback_global:
        return _windows_from_snapshot(
            fallback_global,
            thresholds,
            origin_windows=fallback_origin_global,
        )

    # Prefer global row thresholds when present (logging auto thresholds attach there).
    thr_by_sec: dict[int, object] = {}
    for w in fallback_global or []:
        try:
            sec = int(w.get("sec", 0))
        except (TypeError, ValueError):
            continue
        if sec > 0 and w.get("threshold") is not None:
            thr_by_sec[sec] = w.get("threshold")

    return [
        _window_row(
            sec,
            by_sec[sec],
            thresholds,
            threshold=thr_by_sec.get(sec),
            origin_requests=origin_by_sec.get(sec, 0),
        )
        for sec in order
    ]


@router.get("/stats")
async def traffic_stats(
    site_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    redis = get_redis()
    raw = await redis.get(SNAPSHOT_KEY)
    logging_cfg = await waf_settings.get_logging_settings(db)
    thresholds = {
        int(t["window_sec"]): int(t["max_requests"])
        for t in logging_cfg.get("logging_auto_thresholds") or DEFAULT_AUTO_THRESHOLDS
    }

    if raw:
        try:
            data = json.loads(raw)
            sites_map = data.get("sites") or {}
            global_windows = data.get("global", {}).get("windows") or []
            global_origin_windows = data.get("global", {}).get("origin_windows") or []
            if site_id is None:
                # All-sites: total requests across sites, QPS = total / window.
                windows = _windows_sum_sites(
                    sites_map,
                    thresholds,
                    fallback_global=global_windows,
                    fallback_origin_global=global_origin_windows,
                )
                burst_active = bool(data.get("global", {}).get("burst_active"))
            else:
                site_data = sites_map.get(str(site_id), {})
                windows = _windows_from_snapshot(
                    site_data.get("windows") or [],
                    thresholds,
                    origin_windows=site_data.get("origin_windows") or [],
                )
                burst_active = bool(data.get("global", {}).get("burst_active"))
            return ok({
                "updated_at": data.get("updated_at"),
                "site_id": site_id,
                "global": data.get("global", {}),
                "sites": list(sites_map.keys()),
                "site_count": len(sites_map),
                "windows": windows,
                "burst_active": burst_active,
            })
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return ok({
        "updated_at": None,
        "site_id": site_id,
        "global": {"windows": _default_windows(thresholds), "burst_active": False},
        "sites": [],
        "site_count": 0,
        "windows": _default_windows(thresholds),
        "burst_active": False,
    })
