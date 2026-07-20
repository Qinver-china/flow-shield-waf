"""Serialized, retry-safe database schema bootstrap for multi-process startup."""

from __future__ import annotations

import asyncio
import fcntl
import logging
from pathlib import Path

from app.core.config import settings
from app.core.db import engine
from app.models import Base
from app.services.schema_patches import apply_schema_patches

log = logging.getLogger("waf.schema.bootstrap")

_LOCK_PATH = Path(settings.db_path).with_suffix(".bootstrap.lock")


async def ensure_database_schema(*, max_attempts: int = 8) -> None:
    """Create missing tables and apply schema patches once across concurrent starters."""
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, max_attempts + 1):
        try:
            with open(_LOCK_PATH, "w") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    async with engine.begin() as conn:
                        await conn.run_sync(Base.metadata.create_all)
                        await apply_schema_patches(conn)
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            return
        except Exception as exc:  # noqa: BLE001
            if attempt >= max_attempts:
                raise
            delay = min(0.5 * (2 ** (attempt - 1)), 5.0)
            log.warning(
                "schema bootstrap retry %s/%s in %.1fs after error: %s",
                attempt,
                max_attempts,
                delay,
                exc,
            )
            await asyncio.sleep(delay)
