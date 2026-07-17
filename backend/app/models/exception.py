from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# scope: all | rules | ratelimit
SCOPES = ("all", "rules", "ratelimit")


class Exception_(Base, TimestampMixin):
    """Protection exception. Class name has trailing underscore to avoid the
    Python built-in `Exception`."""

    __tablename__ = "exception"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    site_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    scope: Mapped[str] = mapped_column(String(16), default="all")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
