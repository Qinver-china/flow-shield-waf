"""Lightweight schema patches for model-driven deployments without Alembic."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.core.db import engine

log = logging.getLogger("waf.schema")


async def apply_schema_patches(conn=None) -> None:
    if conn is None:
        async with engine.begin() as connection:
            await _apply_schema_patches(connection)
        return
    await _apply_schema_patches(conn)


async def _apply_schema_patches(conn) -> None:
    await _ensure_waf_setting_timezone(conn)
    await _ensure_waf_setting_ratelimit_fail_open(conn)


async def _ensure_waf_setting_timezone(conn) -> None:
    result = await conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'waf_setting' AND COLUMN_NAME = 'timezone'"
        )
    )
    if int(result.scalar_one()) > 0:
        return
    await conn.execute(
        text(
            "ALTER TABLE waf_setting "
            "ADD COLUMN timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Shanghai'"
        )
    )
    log.info("schema patch applied: waf_setting.timezone")


async def _ensure_waf_setting_ratelimit_fail_open(conn) -> None:
    result = await conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'waf_setting' AND COLUMN_NAME = 'ratelimit_fail_open'"
        )
    )
    if int(result.scalar_one()) > 0:
        return
    await conn.execute(
        text(
            "ALTER TABLE waf_setting "
            "ADD COLUMN ratelimit_fail_open TINYINT(1) NOT NULL DEFAULT 1"
        )
    )
    log.info("schema patch applied: waf_setting.ratelimit_fail_open")
