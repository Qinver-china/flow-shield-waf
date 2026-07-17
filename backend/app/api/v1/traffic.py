import json

from fastapi import APIRouter, Depends
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


@router.get("/stats")
async def traffic_stats(
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
            windows = data.get("global", {}).get("windows") or []
            for w in windows:
                sec = int(w.get("sec", 0))
                if w.get("threshold") is None:
                    w["threshold"] = thresholds.get(sec)
            return ok({
                "updated_at": data.get("updated_at"),
                "global": data.get("global", {}),
                "burst_active": data.get("global", {}).get("burst_active", False),
            })
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    windows = []
    for t in logging_cfg.get("logging_auto_thresholds") or DEFAULT_AUTO_THRESHOLDS:
        sec = int(t["window_sec"])
        windows.append({
            "sec": sec,
            "requests": 0,
            "qps": 0.0,
            "threshold": int(t["max_requests"]),
        })
    return ok({
        "updated_at": None,
        "global": {"windows": windows, "burst_active": False},
        "burst_active": False,
    })
