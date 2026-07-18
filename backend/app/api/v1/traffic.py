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
            "threshold": thresholds.get(sec, int(t["max_requests"])),
        })
    return windows


def _windows_from_snapshot(
    snapshot_windows: list[dict],
    thresholds: dict[int, int],
) -> list[dict]:
    out: list[dict] = []
    for w in snapshot_windows:
        sec = int(w.get("sec", 0))
        out.append({
            "sec": sec,
            "requests": int(w.get("requests") or 0),
            "qps": float(w.get("qps") or 0),
            "threshold": w.get("threshold") if w.get("threshold") is not None else thresholds.get(sec),
        })
    return out


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
            if site_id is None:
                windows = _windows_from_snapshot(
                    data.get("global", {}).get("windows") or [],
                    thresholds,
                )
                burst_active = bool(data.get("global", {}).get("burst_active"))
            else:
                site_data = (data.get("sites") or {}).get(str(site_id), {})
                windows = _windows_from_snapshot(site_data.get("windows") or [], thresholds)
                burst_active = bool(data.get("global", {}).get("burst_active"))
            return ok({
                "updated_at": data.get("updated_at"),
                "site_id": site_id,
                "global": data.get("global", {}),
                "sites": list((data.get("sites") or {}).keys()),
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
        "windows": _default_windows(thresholds),
        "burst_active": False,
    })
