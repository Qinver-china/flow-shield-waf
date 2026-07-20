"""Lightweight schema patches for model-driven deployments without Alembic."""

from __future__ import annotations

import logging

from sqlalchemy import text

log = logging.getLogger("waf.schema")


async def apply_schema_patches(conn=None) -> None:
    if conn is None:
        from app.core.db import engine

        async with engine.begin() as connection:
            await _apply_schema_patches(connection)
        return
    await _apply_schema_patches(conn)


async def _apply_schema_patches(conn) -> None:
    await _ensure_waf_setting_timezone(conn)
    await _ensure_waf_setting_ratelimit_fail_open(conn)
    await _ensure_site_extra_domains(conn)
    await _ensure_site_client_ip_source(conn)
    await _ensure_site_force_https(conn)
    await _ensure_resource_block_page_columns(conn)
    await _drop_legacy_bot_columns(conn)
    await _ensure_waf_setting_panel_public_url(conn)


async def _ensure_resource_block_page_columns(conn) -> None:
    for table in ("rule", "rate_limit", "ip_list"):
        if not await _column_exists(conn, table, "custom_block_page_enabled"):
            await conn.execute(
                text(
                    f"ALTER TABLE {table} "
                    "ADD COLUMN custom_block_page_enabled BOOLEAN NOT NULL DEFAULT 0"
                )
            )
            log.info("schema patch applied: %s.custom_block_page_enabled", table)
        if not await _column_exists(conn, table, "block_page_status_code"):
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN block_page_status_code INTEGER NULL")
            )
            log.info("schema patch applied: %s.block_page_status_code", table)
        if not await _column_exists(conn, table, "block_page_html"):
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN block_page_html TEXT NULL"))
            log.info("schema patch applied: %s.block_page_html", table)


async def _column_exists(conn, table: str, column: str) -> bool:
    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result.fetchall())


async def _drop_legacy_bot_columns(conn) -> None:
    for table, column in (
        ("bot_profile", "action"),
        ("waf_setting", "bot_management_enabled"),
        ("waf_setting", "bot_unknown_action"),
    ):
        if not await _column_exists(conn, table, column):
            continue
        # SQLite lacks DROP COLUMN on older versions; recreate not needed if absent on fresh installs.
        try:
            await conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))
            log.info("schema patch applied: dropped %s.%s", table, column)
        except Exception:  # noqa: BLE001
            log.warning("could not drop legacy column %s.%s", table, column)


async def _ensure_site_extra_domains(conn) -> None:
    if await _column_exists(conn, "site", "extra_domains"):
        return
    await conn.execute(text("ALTER TABLE site ADD COLUMN extra_domains TEXT NULL"))
    log.info("schema patch applied: site.extra_domains")


async def _ensure_site_client_ip_source(conn) -> None:
    if await _column_exists(conn, "site", "client_ip_source"):
        return
    await conn.execute(
        text(
            "ALTER TABLE site "
            "ADD COLUMN client_ip_source VARCHAR(32) NOT NULL DEFAULT 'remote_addr'"
        )
    )
    log.info("schema patch applied: site.client_ip_source")


async def _ensure_site_force_https(conn) -> None:
    if await _column_exists(conn, "site", "force_https"):
        return
    await conn.execute(
        text("ALTER TABLE site ADD COLUMN force_https BOOLEAN NOT NULL DEFAULT 0")
    )
    log.info("schema patch applied: site.force_https")


async def _ensure_waf_setting_timezone(conn) -> None:
    if await _column_exists(conn, "waf_setting", "timezone"):
        return
    await conn.execute(
        text(
            "ALTER TABLE waf_setting "
            "ADD COLUMN timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Shanghai'"
        )
    )
    log.info("schema patch applied: waf_setting.timezone")


async def _ensure_waf_setting_ratelimit_fail_open(conn) -> None:
    if await _column_exists(conn, "waf_setting", "ratelimit_fail_open"):
        return
    await conn.execute(
        text(
            "ALTER TABLE waf_setting "
            "ADD COLUMN ratelimit_fail_open BOOLEAN NOT NULL DEFAULT 1"
        )
    )
    log.info("schema patch applied: waf_setting.ratelimit_fail_open")


async def _ensure_waf_setting_panel_public_url(conn) -> None:
    if await _column_exists(conn, "waf_setting", "panel_public_url"):
        return
    await conn.execute(
        text("ALTER TABLE waf_setting ADD COLUMN panel_public_url VARCHAR(512) NULL")
    )
    log.info("schema patch applied: waf_setting.panel_public_url")
