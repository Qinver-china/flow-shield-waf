from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TrafficBaseline(Base, TimestampMixin):
    """Learned normal request volume per scope + analysis window."""

    __tablename__ = "traffic_baseline"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    window_sec: Mapped[int] = mapped_column(Integer, index=True)
    slot_key: Mapped[str] = mapped_column(String(64), default="same_slot")
    strategy: Mapped[str] = mapped_column(String(64), default="same_slot_hourly")
    avg_requests: Mapped[float] = mapped_column(Float, default=0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
