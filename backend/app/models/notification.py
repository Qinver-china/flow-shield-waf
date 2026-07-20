from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class NotificationChannel(Base, TimestampMixin):
    __tablename__ = "notification_channel"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    channel_type: Mapped[str] = mapped_column(String(24), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AlertPolicy(Base, TimestampMixin):
    __tablename__ = "alert_policy"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    condition_type: Mapped[str] = mapped_column(String(64), index=True)
    condition_params: Mapped[dict] = mapped_column(JSON, default=dict)
    channel_ids: Mapped[list] = mapped_column(JSON, default=list)
    cooldown_sec: Mapped[int] = mapped_column(Integer, default=300)
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
