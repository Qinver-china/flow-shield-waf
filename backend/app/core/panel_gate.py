"""Panel security-entrance cookies shared with nginx map tokens."""
from __future__ import annotations

import hashlib
import hmac

from fastapi import Response

from app.core.config import settings

SESSION_COOKIE = "waf_panel_session"


def entrance_enabled() -> bool:
    return bool(settings.panel_entrance.strip().strip("/"))


def panel_session_token() -> str:
    return hmac.new(
        settings.jwt_secret.encode(),
        b"panel_session",
        hashlib.sha256,
    ).hexdigest()


def session_cookie_max_age() -> int:
    return max(int(settings.jwt_refresh_ttl_days), 1) * 86400


def attach_session_cookie(response: Response) -> None:
    """Mark this browser as logged in so nginx skips the entrance for app pages."""
    if not entrance_enabled():
        return
    response.set_cookie(
        key=SESSION_COOKIE,
        value=panel_session_token(),
        max_age=session_cookie_max_age(),
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
