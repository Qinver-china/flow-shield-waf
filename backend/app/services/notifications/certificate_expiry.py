"""Certificate expiry notification checks and dispatch."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Certificate
from app.models.notification import NotificationChannel
from app.services.notifications.channels import send_via_channel
from app.services.notifications.email_templates import build_cert_expiry_email
from app.services.traffic_intel.timezone import get_traffic_timezone, local_datetime

log = logging.getLogger("waf.notify.cert_expiry")

NOTIFY_DAYS_BEFORE = 7
NOTIFY_LOCAL_HOUR = 10


def days_until_expiry(
    *,
    not_after_utc: datetime,
    now_utc: datetime,
    timezone_name: str,
) -> int:
    """Calendar days from local today to local expiry date (may be negative)."""
    now_local = local_datetime(now_utc, timezone_name)
    expiry_local = local_datetime(not_after_utc, timezone_name)
    return (expiry_local.date() - now_local.date()).days


def should_notify_today(
    *,
    enabled: bool,
    channel_id: int | None,
    not_after: datetime | None,
    last_notified_on: str | None,
    now_utc: datetime,
    timezone_name: str,
) -> bool:
    if not enabled or not channel_id or not_after is None:
        return False
    now_local = local_datetime(now_utc, timezone_name)
    if now_local.hour < NOTIFY_LOCAL_HOUR:
        return False
    today = now_local.date().isoformat()
    if last_notified_on == today:
        return False
    days_left = days_until_expiry(
        not_after_utc=not_after,
        now_utc=now_utc,
        timezone_name=timezone_name,
    )
    return 0 <= days_left <= NOTIFY_DAYS_BEFORE


async def run_certificate_expiry_checks(db: AsyncSession) -> int:
    """Send at most one expiry notice per certificate per local day. Returns send count."""
    timezone_name = await get_traffic_timezone(db)
    now_utc = datetime.utcnow()
    now_local = local_datetime(now_utc, timezone_name)
    if now_local.hour < NOTIFY_LOCAL_HOUR:
        return 0

    today = now_local.date().isoformat()
    rows = (
        await db.execute(
            select(Certificate).where(
                Certificate.expiry_notify_enabled.is_(True),
                Certificate.expiry_notify_channel_id.is_not(None),
                Certificate.not_after.is_not(None),
            )
        )
    ).scalars().all()

    sent = 0
    for cert in rows:
        if not should_notify_today(
            enabled=bool(cert.expiry_notify_enabled),
            channel_id=cert.expiry_notify_channel_id,
            not_after=cert.not_after,
            last_notified_on=cert.expiry_last_notified_on,
            now_utc=now_utc,
            timezone_name=timezone_name,
        ):
            continue

        channel = await db.get(NotificationChannel, cert.expiry_notify_channel_id)
        if channel is None or not channel.enabled:
            log.warning(
                "cert expiry notify skipped id=%s: channel missing or disabled",
                cert.id,
            )
            continue

        days_left = days_until_expiry(
            not_after_utc=cert.not_after,  # type: ignore[arg-type]
            now_utc=now_utc,
            timezone_name=timezone_name,
        )
        expiry_local = local_datetime(cert.not_after, timezone_name)  # type: ignore[arg-type]
        domains = (cert.domains or "").strip() or "（无域名）"
        subject = f"流盾WAF 证书即将到期：{cert.name}"
        plain, html_body = build_cert_expiry_email(
            cert_name=cert.name,
            domains=domains,
            not_after_local=expiry_local.strftime("%Y-%m-%d %H:%M:%S"),
            days_left=days_left,
            timezone_name=timezone_name,
        )
        try:
            await send_via_channel(
                channel,
                subject=subject,
                body=plain,
                html_body=html_body,
            )
        except Exception:  # noqa: BLE001
            log.exception("cert expiry notify failed id=%s channel=%s", cert.id, channel.id)
            continue

        cert.expiry_last_notified_on = today
        sent += 1
        log.info(
            "cert expiry notified id=%s name=%s days_left=%s date=%s",
            cert.id,
            cert.name,
            days_left,
            today,
        )

    if sent:
        await db.commit()
    return sent
