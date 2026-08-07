from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Certificate(Base, TimestampMixin):
    __tablename__ = "certificate"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    domains: Mapped[str | None] = mapped_column(Text, nullable=True)
    cert_path: Mapped[str] = mapped_column(String(512))
    key_path: Mapped[str] = mapped_column(String(512))
    not_before: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    not_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expiry_notify_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    expiry_notify_channel_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Local calendar date (YYYY-MM-DD) of last successful expiry notification.
    expiry_last_notified_on: Mapped[str | None] = mapped_column(String(10), nullable=True)
