"""Simple Redis-backed rate limiting for sensitive endpoints."""
from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core.redis import get_redis

LOGIN_LIMIT = 10
LOGIN_WINDOW_SEC = 300


async def check_login_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    key = f"waf:ratelimit:login:{client}"
    redis = get_redis()
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, LOGIN_WINDOW_SEC)
    if count > LOGIN_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录尝试过于频繁，请稍后再试",
        )
