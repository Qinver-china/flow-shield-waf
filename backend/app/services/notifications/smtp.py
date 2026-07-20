"""SMTP email delivery."""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.header import Header
from email.message import EmailMessage
from email.utils import formataddr, formatdate

from app.schemas.notification import EmailChannelConfig

log = logging.getLogger("waf.notify.smtp")


def _send_sync(
    cfg: EmailChannelConfig,
    subject: str,
    body: str,
    *,
    html_body: str | None = None,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"] = formataddr((cfg.from_name, cfg.from_address))
    msg["To"] = ", ".join(cfg.to_addresses)
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(body, subtype="plain", charset="utf-8")
    if html_body:
        msg.add_alternative(html_body, subtype="html", charset="utf-8")

    if cfg.smtp_security == "ssl":
        server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=30)
    else:
        server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30)
    try:
        if cfg.smtp_security == "starttls":
            server.starttls()
        if cfg.smtp_user:
            server.login(cfg.smtp_user, cfg.smtp_password)
        server.send_message(msg, from_addr=cfg.from_address, to_addrs=cfg.to_addresses)
    finally:
        server.quit()


async def send_email(
    cfg: EmailChannelConfig,
    subject: str,
    body: str,
    *,
    html_body: str | None = None,
) -> None:
    await asyncio.to_thread(_send_sync, cfg, subject, body, html_body=html_body)
    log.info("email sent to %s subject=%s", cfg.to_addresses, subject)
