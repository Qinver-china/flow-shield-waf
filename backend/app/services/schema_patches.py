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
    await _ensure_site_extra_domains(conn)
    await _ensure_resource_block_page_columns(conn)
    await _drop_legacy_bot_columns(conn)


async def _ensure_resource_block_page_columns(conn) -> None:
    for table in ("rule", "rate_limit", "ip_list"):
        if not await _column_exists(conn, table, "custom_block_page_enabled"):
            await conn.execute(
                text(
                    f"ALTER TABLE {table} "
                    "ADD COLUMN custom_block_page_enabled TINYINT(1) NOT NULL DEFAULT 0"
                )
            )
            log.info("schema patch applied: %s.custom_block_page_enabled", table)
        if not await _column_exists(conn, table, "block_page_status_code"):
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN block_page_status_code INT NULL")
            )
            log.info("schema patch applied: %s.block_page_status_code", table)
        if not await _column_exists(conn, table, "block_page_html"):
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN block_page_html TEXT NULL"))
            log.info("schema patch applied: %s.block_page_html", table)


async def _column_exists(conn, table: str, column: str) -> bool:
    result = await conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            f"AND TABLE_NAME = '{table}' AND COLUMN_NAME = '{column}'"
        )
    )
    return int(result.scalar_one()) > 0


async def _drop_legacy_bot_columns(conn) -> None:
    for table, column in (
        ("bot_profile", "action"),
        ("waf_setting", "bot_management_enabled"),
        ("waf_setting", "bot_unknown_action"),
    ):
        if not await _column_exists(conn, table, column):
            continue
        await conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))
        log.info("schema patch applied: dropped %s.%s", table, column)


async def _ensure_site_extra_domains(conn) -> None:
    result = await conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'site' AND COLUMN_NAME = 'extra_domains'"
        )
    )
    if int(result.scalar_one()) > 0:
        return
    await conn.execute(text("ALTER TABLE site ADD COLUMN extra_domains TEXT NULL"))
    log.info("schema patch applied: site.extra_domains")


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

