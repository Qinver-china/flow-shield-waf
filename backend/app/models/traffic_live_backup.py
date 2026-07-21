"""Lightweight SQLite backup for live traffic windows (Redis is authoritative)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Windows persisted to DB backup (exclude live-only 10s).
BACKUP_WINDOW_SECS = (30, 60, 300, 1800, 3600, 86400)
BACKUP_INTERVAL_SEC = 30
REDIS_SNAPSHOT_KEY = "waf:traffic:snapshot"
REDIS_MIN_G = "waf:traffic:min:g"
REDIS_MIN_S_PREFIX = "waf:traffic:min:s:"


class TrafficLiveBackup(Base):
    """Singleton row: compact JSON of window totals + sparse minute rings."""

    __tablename__ = "traffic_live_backup"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
