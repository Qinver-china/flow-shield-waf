"""Timezone helpers for traffic baseline slot alignment."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.display_settings import DEFAULT_TIMEZONE
from app.services.waf_settings import get_or_create

# Fallback when IANA tzdata is unavailable (e.g. minimal Alpine image).
_FIXED_OFFSETS: dict[str, timezone] = {
    "Asia/Shanghai": timezone(timedelta(hours=8)),
    "Asia/Hong_Kong": timezone(timedelta(hours=8)),
    "Asia/Taipei": timezone(timedelta(hours=8)),
    "UTC": timezone.utc,
}


def _resolve_zone(name: str) -> timezone | ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name in _FIXED_OFFSETS:
            return _FIXED_OFFSETS[name]
        try:
            return ZoneInfo(DEFAULT_TIMEZONE)
        except ZoneInfoNotFoundError:
            return _FIXED_OFFSETS.get(DEFAULT_TIMEZONE, timezone(timedelta(hours=8)))


async def get_traffic_timezone(db: AsyncSession) -> str:
    row = await get_or_create(db)
    tz = getattr(row, "timezone", None) or DEFAULT_TIMEZONE
    try:
        ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        if tz in _FIXED_OFFSETS:
            return tz
        return DEFAULT_TIMEZONE
    return tz


def local_datetime(dt: datetime, timezone_name: str) -> datetime:
    """Convert naive UTC datetime to naive local wall-clock time."""
    aware = dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(_resolve_zone(timezone_name)).replace(tzinfo=None)
