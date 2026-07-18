from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BotProfile(Base, TimestampMixin):
    """Known bot definitions matched by User-Agent patterns."""

    __tablename__ = "bot_profile"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32), default="other")
    ua_patterns: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    site_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    verify_dns_suffix: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
