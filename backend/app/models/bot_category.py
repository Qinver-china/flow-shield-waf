from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BotCategory(Base, TimestampMixin):
    """Managed bot classification labels referenced by bot profiles and rules."""

    __tablename__ = "bot_category"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    value: Mapped[str] = mapped_column(String(32), unique=True)
    label: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
