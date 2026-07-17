"""Serialized, retry-safe database schema bootstrap for multi-process startup."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.db import engine
from app.models import Base
from app.services.schema_patches import apply_schema_patches

log = logging.getLogger("waf.schema.bootstrap")

_LOCK_NAME = "flowshield_schema_bootstrap"
_LOCK_TIMEOUT_SEC = 120
_RETRYABLE_MYSQL_ERRNOS = {1205, 1213, 1684, 3572}


def _is_retryable_schema_error(exc: OperationalError) -> bool:
    orig = getattr(exc, "orig", None)
    args = getattr(orig, "args", ())
    if not args:
        return False
    try:
        return int(args[0]) in _RETRYABLE_MYSQL_ERRNOS
    except (TypeError, ValueError):
        return False


async def _acquire_bootstrap_lock(conn) -> bool:
    result = await conn.execute(
        text("SELECT GET_LOCK(:name, :timeout)"),
        {"name": _LOCK_NAME, "timeout": _LOCK_TIMEOUT_SEC},
    )
    return int(result.scalar_one() or 0) == 1


async def _release_bootstrap_lock(conn) -> None:
    await conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": _LOCK_NAME})


async def ensure_database_schema(*, max_attempts: int = 8) -> None:
    """Create missing tables and apply schema patches once across concurrent starters."""
    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.begin() as conn:
                if not await _acquire_bootstrap_lock(conn):
                    raise RuntimeError("timed out waiting for schema bootstrap lock")
                try:
                    await conn.run_sync(Base.metadata.create_all)
                    await apply_schema_patches(conn)
                finally:
                    await _release_bootstrap_lock(conn)
            return
        except OperationalError as exc:
            if attempt >= max_attempts or not _is_retryable_schema_error(exc):
                raise
            delay = min(0.5 * (2 ** (attempt - 1)), 5.0)
            log.warning(
                "schema bootstrap retry %s/%s in %.1fs after transient MySQL error: %s",
                attempt,
                max_attempts,
                delay,
                exc,
            )
            await asyncio.sleep(delay)
