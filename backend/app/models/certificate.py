from datetime import datetime

from sqlalchemy import DateTime, String, Text
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
