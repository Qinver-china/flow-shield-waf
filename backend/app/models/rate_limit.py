from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RateLimit(Base, TimestampMixin):
    __tablename__ = "rate_limit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    site_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # list of {field, arg?} used to build the rate-limit key
    keys: Mapped[list] = mapped_column(JSON, default=list)
    window: Mapped[int] = mapped_column(Integer, default=60)
    threshold: Mapped[int] = mapped_column(Integer, default=100)
    mode: Mapped[str] = mapped_column(String(24), default="block")
    # optional precondition (unified condition tree); empty => always apply
    conditions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_block_page_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    block_page_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_page_html: Mapped[str | None] = mapped_column(Text, nullable=True)
