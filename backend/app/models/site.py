from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.certificate import Certificate


class Site(Base, TimestampMixin):
    __tablename__ = "site"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    origin_host: Mapped[str] = mapped_column(String(255))
    origin_protocol: Mapped[str] = mapped_column(String(16), default="follow")
    origin_http_port: Mapped[int] = mapped_column(Integer, default=80)
    origin_https_port: Mapped[int] = mapped_column(Integer, default=443)
    listen_http: Mapped[bool] = mapped_column(Boolean, default=True)
    listen_https: Mapped[bool] = mapped_column(Boolean, default=False)
    certificate_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("certificate.id"), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_block_page_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    block_page_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_page_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_captcha_footer_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    captcha_footer_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    certificate: Mapped[Certificate | None] = relationship(
        "Certificate", lazy="joined", foreign_keys=[certificate_id]
    )
