from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class IpGroup(Base, TimestampMixin):
    """Reusable IP/CIDR collections referenced by rule conditions."""

    __tablename__ = "ip_group"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entries: Mapped[list] = mapped_column(JSON, default=list)
