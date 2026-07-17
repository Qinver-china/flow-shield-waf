from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class IpList(Base, TimestampMixin):
    """Global black / white list. `list_type` = 'black' | 'white'."""

    __tablename__ = "ip_list"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    list_type: Mapped[str] = mapped_column(String(16), index=True)  # black | white
    name: Mapped[str] = mapped_column(String(128))
    site_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
