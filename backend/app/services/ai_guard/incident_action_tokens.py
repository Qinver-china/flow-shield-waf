"""Short-lived signed tokens for incident actions from email links."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt

from app.core.config import settings

IncidentAction = Literal["apply", "dismiss"]
INCIDENT_ACTION_TTL_MIN = 10


def create_incident_action_token(incident_id: int, action: IncidentAction) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "type": "incident_action",
        "action": action,
        "incident_id": int(incident_id),
        "iat": now,
        "exp": now + timedelta(minutes=INCIDENT_ACTION_TTL_MIN),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_incident_action_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "incident_action":
        raise ValueError("无效的令牌类型")
    action = payload.get("action")
    if action not in ("apply", "dismiss"):
        raise ValueError("无效的操作")
    incident_id = payload.get("incident_id")
    if incident_id is None:
        raise ValueError("缺少事件 ID")
    return {
        "action": action,
        "incident_id": int(incident_id),
    }
