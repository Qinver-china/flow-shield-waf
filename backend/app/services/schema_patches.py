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
    await _ensure_site_custom_listen_ports(conn)
    await _ensure_site_disable_content_buffering(conn)
    await _ensure_resource_block_page_columns(conn)
    await _drop_legacy_bot_columns(conn)
    await _ensure_bot_profile_categories(conn)
    await _ensure_waf_setting_panel_public_url(conn)
    await _drop_waf_setting_admin_credentials_set(conn)
    await _ensure_ai_guard_floating_chat_enabled(conn)
    await _ensure_ai_guard_defense_web_search_enabled(conn)
    await _ensure_ai_guard_policy_custom_prompt(conn)
    await _ensure_rule_remark(conn)
    await _ensure_certificate_expiry_notify(conn)
    await _ensure_certificate_acme_columns(conn)
    await _ensure_certificate_panel_push_columns(conn)
    await _ensure_waf_setting_acme_account_email(conn)
    await _ensure_waf_setting_max_upload_size_mb(conn)
    await _ensure_waf_setting_origin_read_timeout_sec(conn)
    await _upgrade_default_response_page_brand_links(conn)


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
    await conn.execute(text("ALTER TABLE site ADD COLUMN force_https BOOLEAN NOT NULL DEFAULT 0"))
    log.info("schema patch applied: site.force_https")


async def _ensure_site_custom_listen_ports(conn) -> None:
    if not await _column_exists(conn, "site", "custom_listen_ports"):
        await conn.execute(
            text("ALTER TABLE site " "ADD COLUMN custom_listen_ports BOOLEAN NOT NULL DEFAULT 0")
        )
        log.info("schema patch applied: site.custom_listen_ports")
    if not await _column_exists(conn, "site", "listen_http_ports"):
        await conn.execute(
            text(
                "ALTER TABLE site "
                "ADD COLUMN listen_http_ports VARCHAR(255) NOT NULL DEFAULT '80'"
            )
        )
        log.info("schema patch applied: site.listen_http_ports")
    if not await _column_exists(conn, "site", "listen_https_ports"):
        await conn.execute(
            text(
                "ALTER TABLE site "
                "ADD COLUMN listen_https_ports VARCHAR(255) NOT NULL DEFAULT '443'"
            )
        )
        log.info("schema patch applied: site.listen_https_ports")


async def _ensure_site_disable_content_buffering(conn) -> None:
    if await _column_exists(conn, "site", "disable_content_buffering"):
        return
    await conn.execute(
        text("ALTER TABLE site " "ADD COLUMN disable_content_buffering BOOLEAN NOT NULL DEFAULT 0")
    )
    log.info("schema patch applied: site.disable_content_buffering")


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
        text("ALTER TABLE waf_setting " "ADD COLUMN ratelimit_fail_open BOOLEAN NOT NULL DEFAULT 1")
    )
    log.info("schema patch applied: waf_setting.ratelimit_fail_open")


async def _ensure_bot_profile_categories(conn) -> None:
    """Migrate bot_profile.category (string) -> categories (JSON array)."""
    has_categories = await _column_exists(conn, "bot_profile", "categories")
    has_category = await _column_exists(conn, "bot_profile", "category")
    if not has_categories:
        await conn.execute(text("ALTER TABLE bot_profile ADD COLUMN categories JSON"))
        log.info("schema patch applied: bot_profile.categories")
        has_categories = True
    if has_categories and has_category:
        await conn.execute(
            text(
                "UPDATE bot_profile "
                "SET categories = json_array(category) "
                "WHERE (categories IS NULL OR categories = '' OR categories = 'null' OR categories = '[]') "
                "AND category IS NOT NULL AND category != ''"
            )
        )
        await conn.execute(
            text(
                "UPDATE bot_profile "
                "SET categories = json_array('other') "
                "WHERE categories IS NULL OR categories = '' OR categories = 'null' OR categories = '[]'"
            )
        )
        try:
            await conn.execute(text("ALTER TABLE bot_profile DROP COLUMN category"))
            log.info("schema patch applied: dropped bot_profile.category")
        except Exception:  # noqa: BLE001
            log.warning("could not drop legacy column bot_profile.category")
    elif has_categories:
        await conn.execute(
            text(
                "UPDATE bot_profile "
                "SET categories = json_array('other') "
                "WHERE categories IS NULL OR categories = '' OR categories = 'null' OR categories = '[]'"
            )
        )


async def _ensure_waf_setting_panel_public_url(conn) -> None:
    if await _column_exists(conn, "waf_setting", "panel_public_url"):
        return
    await conn.execute(
        text("ALTER TABLE waf_setting ADD COLUMN panel_public_url VARCHAR(512) NULL")
    )
    log.info("schema patch applied: waf_setting.panel_public_url")


async def _drop_waf_setting_admin_credentials_set(conn) -> None:
    if not await _column_exists(conn, "waf_setting", "admin_credentials_set"):
        return
    try:
        await conn.execute(text("ALTER TABLE waf_setting DROP COLUMN admin_credentials_set"))
        log.info("schema patch applied: dropped waf_setting.admin_credentials_set")
    except Exception:  # noqa: BLE001
        log.warning("could not drop legacy column waf_setting.admin_credentials_set")


async def _ensure_ai_guard_floating_chat_enabled(conn) -> None:
    if await _column_exists(conn, "ai_guard_setting", "floating_chat_enabled"):
        return
    await conn.execute(
        text(
            "ALTER TABLE ai_guard_setting "
            "ADD COLUMN floating_chat_enabled BOOLEAN NOT NULL DEFAULT 1"
        )
    )
    log.info("schema patch applied: ai_guard_setting.floating_chat_enabled")


async def _ensure_ai_guard_defense_web_search_enabled(conn) -> None:
    """Add the opt-in switch for external search during automated defense."""
    if await _column_exists(conn, "ai_guard_setting", "defense_web_search_enabled"):
        return
    await conn.execute(
        text(
            "ALTER TABLE ai_guard_setting "
            "ADD COLUMN defense_web_search_enabled BOOLEAN NOT NULL DEFAULT 0"
        )
    )
    log.info("schema patch applied: ai_guard_setting.defense_web_search_enabled")


async def _ensure_ai_guard_policy_custom_prompt(conn) -> None:
    if await _column_exists(conn, "ai_guard_policy", "custom_prompt"):
        return
    await conn.execute(text("ALTER TABLE ai_guard_policy ADD COLUMN custom_prompt TEXT NULL"))
    log.info("schema patch applied: ai_guard_policy.custom_prompt")


async def _ensure_rule_remark(conn) -> None:
    if await _column_exists(conn, "rule", "remark"):
        return
    await conn.execute(text("ALTER TABLE rule ADD COLUMN remark VARCHAR(255) NULL"))
    log.info("schema patch applied: rule.remark")


async def _ensure_certificate_expiry_notify(conn) -> None:
    if not await _column_exists(conn, "certificate", "expiry_notify_enabled"):
        await conn.execute(
            text(
                "ALTER TABLE certificate "
                "ADD COLUMN expiry_notify_enabled BOOLEAN NOT NULL DEFAULT 0"
            )
        )
        log.info("schema patch applied: certificate.expiry_notify_enabled")
    if not await _column_exists(conn, "certificate", "expiry_last_notified_on"):
        await conn.execute(
            text("ALTER TABLE certificate ADD COLUMN expiry_last_notified_on VARCHAR(10) NULL")
        )
        log.info("schema patch applied: certificate.expiry_last_notified_on")
    await _ensure_certificate_expiry_notify_channel_ids(conn)


async def _ensure_certificate_expiry_notify_channel_ids(conn) -> None:
    """Migrate certificate.expiry_notify_channel_id -> expiry_notify_channel_ids (JSON)."""
    has_ids = await _column_exists(conn, "certificate", "expiry_notify_channel_ids")
    has_id = await _column_exists(conn, "certificate", "expiry_notify_channel_id")
    if not has_ids:
        await conn.execute(
            text("ALTER TABLE certificate ADD COLUMN expiry_notify_channel_ids JSON")
        )
        log.info("schema patch applied: certificate.expiry_notify_channel_ids")
        has_ids = True
    if has_ids and has_id:
        await conn.execute(
            text(
                "UPDATE certificate "
                "SET expiry_notify_channel_ids = json_array(expiry_notify_channel_id) "
                "WHERE (expiry_notify_channel_ids IS NULL OR expiry_notify_channel_ids = '' "
                "OR expiry_notify_channel_ids = 'null' OR expiry_notify_channel_ids = '[]') "
                "AND expiry_notify_channel_id IS NOT NULL"
            )
        )
        await conn.execute(
            text(
                "UPDATE certificate "
                "SET expiry_notify_channel_ids = json_array() "
                "WHERE expiry_notify_channel_ids IS NULL OR expiry_notify_channel_ids = '' "
                "OR expiry_notify_channel_ids = 'null'"
            )
        )
        try:
            await conn.execute(text("ALTER TABLE certificate DROP COLUMN expiry_notify_channel_id"))
            log.info("schema patch applied: dropped certificate.expiry_notify_channel_id")
        except Exception:  # noqa: BLE001
            log.warning("could not drop legacy column certificate.expiry_notify_channel_id")
    elif has_ids:
        await conn.execute(
            text(
                "UPDATE certificate "
                "SET expiry_notify_channel_ids = json_array() "
                "WHERE expiry_notify_channel_ids IS NULL OR expiry_notify_channel_ids = '' "
                "OR expiry_notify_channel_ids = 'null'"
            )
        )


async def _ensure_certificate_acme_columns(conn) -> None:
    if not await _column_exists(conn, "certificate", "acme_provider"):
        await conn.execute(
            text("ALTER TABLE certificate ADD COLUMN acme_provider VARCHAR(32) NULL")
        )
        log.info("schema patch applied: certificate.acme_provider")
    if not await _column_exists(conn, "certificate", "acme_auto_renew"):
        await conn.execute(
            text("ALTER TABLE certificate " "ADD COLUMN acme_auto_renew BOOLEAN NOT NULL DEFAULT 0")
        )
        log.info("schema patch applied: certificate.acme_auto_renew")
    if not await _column_exists(conn, "certificate", "acme_last_attempt_on"):
        await conn.execute(
            text("ALTER TABLE certificate ADD COLUMN acme_last_attempt_on VARCHAR(10) NULL")
        )
        log.info("schema patch applied: certificate.acme_last_attempt_on")
    if not await _column_exists(conn, "certificate", "acme_last_error"):
        await conn.execute(
            text("ALTER TABLE certificate ADD COLUMN acme_last_error VARCHAR(512) NULL")
        )
        log.info("schema patch applied: certificate.acme_last_error")


async def _ensure_certificate_panel_push_columns(conn) -> None:
    """Add auto-renew panel push columns used to deploy certs to BaoTa / 1Panel."""
    if not await _column_exists(conn, "certificate", "panel_push_enabled"):
        await conn.execute(
            text(
                "ALTER TABLE certificate "
                "ADD COLUMN panel_push_enabled BOOLEAN NOT NULL DEFAULT 0"
            )
        )
        log.info("schema patch applied: certificate.panel_push_enabled")
    if not await _column_exists(conn, "certificate", "panel_push_targets"):
        await conn.execute(text("ALTER TABLE certificate ADD COLUMN panel_push_targets JSON"))
        log.info("schema patch applied: certificate.panel_push_targets")
    await conn.execute(
        text(
            "UPDATE certificate "
            "SET panel_push_targets = json_array() "
            "WHERE panel_push_targets IS NULL OR panel_push_targets = '' "
            "OR panel_push_targets = 'null'"
        )
    )


async def _ensure_waf_setting_acme_account_email(conn) -> None:
    if await _column_exists(conn, "waf_setting", "acme_account_email"):
        return
    await conn.execute(
        text("ALTER TABLE waf_setting ADD COLUMN acme_account_email VARCHAR(254) NULL")
    )
    log.info("schema patch applied: waf_setting.acme_account_email")


async def _ensure_waf_setting_max_upload_size_mb(conn) -> None:
    if await _column_exists(conn, "waf_setting", "max_upload_size_mb"):
        return
    from app.constants.engine_settings import DEFAULT_MAX_UPLOAD_SIZE_MB

    default_mb = int(DEFAULT_MAX_UPLOAD_SIZE_MB)
    await conn.execute(
        text(
            "ALTER TABLE waf_setting "
            f"ADD COLUMN max_upload_size_mb INTEGER NOT NULL DEFAULT {default_mb}"
        )
    )
    log.info("schema patch applied: waf_setting.max_upload_size_mb")


async def _ensure_waf_setting_origin_read_timeout_sec(conn) -> None:
    if await _column_exists(conn, "waf_setting", "origin_read_timeout_sec"):
        return
    from app.constants.engine_settings import DEFAULT_ORIGIN_READ_TIMEOUT_SEC

    default_sec = int(DEFAULT_ORIGIN_READ_TIMEOUT_SEC)
    await conn.execute(
        text(
            "ALTER TABLE waf_setting "
            "ADD COLUMN origin_read_timeout_sec INTEGER NOT NULL "
            f"DEFAULT {default_sec}"
        )
    )
    log.info("schema patch applied: waf_setting.origin_read_timeout_sec")


async def _upgrade_default_response_page_brand_links(conn) -> None:
    """Add official-site links to unmodified default block page / captcha footer HTML."""
    if not await _column_exists(conn, "waf_setting", "block_page_html"):
        return
    from app.constants.response_pages import (
        DEFAULT_BLOCK_PAGE_HTML,
        DEFAULT_CAPTCHA_FOOTER_HTML,
        LEGACY_DEFAULT_BLOCK_PAGE_HTML,
        LEGACY_DEFAULT_CAPTCHA_FOOTER_HTML,
    )

    result = await conn.execute(
        text("UPDATE waf_setting SET block_page_html = :new WHERE block_page_html = :old"),
        {"new": DEFAULT_BLOCK_PAGE_HTML, "old": LEGACY_DEFAULT_BLOCK_PAGE_HTML},
    )
    footer_result = await conn.execute(
        text("UPDATE waf_setting SET captcha_footer_html = :new WHERE captcha_footer_html = :old"),
        {"new": DEFAULT_CAPTCHA_FOOTER_HTML, "old": LEGACY_DEFAULT_CAPTCHA_FOOTER_HTML},
    )
    if result.rowcount or footer_result.rowcount:
        log.info("schema patch applied: default response pages now link to official site")
