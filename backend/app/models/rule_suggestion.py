from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RuleSuggestion(Base, TimestampMixin):
    """Auto-generated rule draft from log analysis (manual trigger only)."""

    __tablename__ = "rule_suggestion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    pattern_json: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(Text, default="")
    sample_request_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")  # pending|accepted|dismissed
