from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# mode: observe | block | captcha | js_challenge | slide_captcha
MODES = ("observe", "block", "captcha", "js_challenge", "slide_captcha")


class Rule(Base, TimestampMixin):
    __tablename__ = "rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    # site_ids NULL / empty => global scope
    site_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    mode: Mapped[str] = mapped_column(String(24), default="block")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    custom_block_page_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    block_page_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_page_html: Mapped[str | None] = mapped_column(Text, nullable=True)
