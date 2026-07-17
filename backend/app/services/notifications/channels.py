"""Send messages through configured notification channels."""
from __future__ import annotations

import logging

from app.models.notification import NotificationChannel
from app.schemas.notification import EmailChannelConfig
from app.services.notifications.smtp import send_email

log = logging.getLogger("waf.notify.channels")

PLACEHOLDER_TYPES = frozenset({"sms", "webhook", "dingtalk"})


def mask_channel_config(channel_type: str, config: dict) -> dict:
    masked = dict(config or {})
    if channel_type == "email" and masked.get("smtp_password"):
        masked["smtp_password"] = "******"
    return masked


def validate_channel_config(channel_type: str, config: dict, *, partial: bool = False) -> dict:
    if channel_type in PLACEHOLDER_TYPES:
        raise ValueError(f"通道类型「{channel_type}」尚未开放，敬请期待")
    if channel_type == "email":
        if partial and not config:
            return {}
        model = EmailChannelConfig.model_validate(config)
        return model.model_dump()
    raise ValueError(f"未知通道类型: {channel_type}")


async def send_via_channel(
    channel: NotificationChannel,
    *,
    subject: str,
    body: str,
) -> None:
    if not channel.enabled:
        raise ValueError(f"通道「{channel.name}」已禁用")
    if channel.channel_type == "email":
        cfg = EmailChannelConfig.model_validate(channel.config or {})
        await send_email(cfg, subject, body)
        return
    raise ValueError(f"通道类型「{channel.channel_type}」尚未实现")
