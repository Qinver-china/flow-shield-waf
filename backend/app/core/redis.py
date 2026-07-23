"""Shared async Redis client with pooling and Unix socket support."""
from redis import asyncio as aioredis

from app.core.config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        kwargs: dict = {
            "password": settings.redis_password or None,
            "encoding": "utf-8",
            # Log stream payloads may contain non-UTF8 bytes (UA/cookie/path).
            # Never crash the shared client on decode; replace and let callers handle.
            "encoding_errors": "replace",
            "decode_responses": True,
            "max_connections": settings.redis_max_connections,
            "socket_keepalive": True,
            "health_check_interval": 30,
            "retry_on_timeout": True,
            "socket_connect_timeout": 2,
            "socket_timeout": 5,
        }
        if settings.redis_socket_path:
            kwargs["unix_socket_path"] = settings.redis_socket_path
        else:
            kwargs["host"] = settings.redis_host
            kwargs["port"] = settings.redis_port
        _redis = aioredis.Redis(**kwargs)
    return _redis
