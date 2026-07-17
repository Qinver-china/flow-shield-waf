"""SMTP email delivery."""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.schemas.notification import EmailChannelConfig

log = logging.getLogger("waf.notify.smtp")


def _send_sync(cfg: EmailChannelConfig, subject: str, body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((cfg.from_name, cfg.from_address))
    msg["To"] = ", ".join(cfg.to_addresses)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if cfg.smtp_security == "ssl":
        server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=30)
    else:
        server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30)
    try:
        if cfg.smtp_security == "starttls":
            server.starttls()
        if cfg.smtp_user:
            server.login(cfg.smtp_user, cfg.smtp_password)
        server.sendmail(cfg.from_address, cfg.to_addresses, msg.as_string())
    finally:
        server.quit()


async def send_email(cfg: EmailChannelConfig, subject: str, body: str) -> None:
    await asyncio.to_thread(_send_sync, cfg, subject, body)
    log.info("email sent to %s subject=%s", cfg.to_addresses, subject)
