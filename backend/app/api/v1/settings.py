import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.models import User
from app.schemas.common import ok
from app.schemas.logging_settings import LoggingSettings, LoggingSettingsOut, traffic_window_options
from app.constants.response_pages import DEFAULT_BLOCK_PAGE_HTML, DEFAULT_CAPTCHA_FOOTER_HTML
from app.schemas.response_pages import (
    BlockPageSettings,
    BlockPageSettingsOut,
    CaptchaFooterSettings,
    CaptchaFooterSettingsOut,
)
from app.schemas.waf_setting import (
    ChallengeSettings,
    ChallengeSettingsOut,
    DebugSettings,
    DebugSettingsOut,
    DisplaySettings,
    DisplaySettingsOut,
)
from app.services import rule_sync, waf_settings
from app.services.logging.retention_ttl import apply_log_retention_ttl

router = APIRouter()


@router.get("/challenge")
async def get_challenge_settings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    return ok(ChallengeSettingsOut.from_row(row).model_dump())


@router.put("/challenge")
async def update_challenge_settings(
    body: ChallengeSettings,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    row.js_challenge_ttl = body.js_challenge_ttl
    row.captcha_ttl = body.captcha_ttl
    row.clearance_fingerprint_dims = json.dumps(
        body.clearance_fingerprint_dims, ensure_ascii=False
    )
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(ChallengeSettingsOut.from_row(row).model_dump())


@router.get("/logging")
async def get_logging_settings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    data = LoggingSettingsOut.from_row(row).model_dump()
    data["traffic_window_options"] = traffic_window_options()
    return ok(data)


@router.put("/logging")
async def update_logging_settings(
    body: LoggingSettings,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    row.logging_control_mode = body.logging_control_mode
    row.logging_enabled = body.logging_enabled
    row.logging_skip_observe = body.logging_skip_observe
    row.observe_sample_rate_idle = body.observe_sample_rate_idle
    row.observe_sample_rate_active = body.observe_sample_rate_active
    row.logging_detail_on_block = body.logging_detail_on_block
    row.logging_auto_thresholds = json.dumps(
        [t.model_dump() for t in body.logging_auto_thresholds], ensure_ascii=False
    )
    row.logging_auto_cooldown_sec = body.logging_auto_cooldown_sec
    row.logging_auto_observe_sample_rate = body.logging_auto_observe_sample_rate
    row.log_retention_days = body.log_retention_days
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    await apply_log_retention_ttl(body.log_retention_days)
    data = LoggingSettingsOut.from_row(row).model_dump()
    data["traffic_window_options"] = traffic_window_options()
    return ok(data)


@router.get("/debug")
async def get_debug_settings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    return ok(DebugSettingsOut.model_validate(row).model_dump())


@router.put("/debug")
async def update_debug_settings(
    body: DebugSettings,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    row.debug_mode = body.debug_mode
    row.ratelimit_fail_open = body.ratelimit_fail_open
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(DebugSettingsOut.model_validate(row).model_dump())


@router.get("/block-page")
async def get_block_page_settings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    return ok(BlockPageSettingsOut(
        status_code=row.block_page_status_code,
        html=row.block_page_html or DEFAULT_BLOCK_PAGE_HTML,
    ).model_dump())


@router.put("/block-page")
async def update_block_page_settings(
    body: BlockPageSettings,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    row.block_page_status_code = body.status_code
    row.block_page_html = body.html
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(BlockPageSettingsOut(
        status_code=row.block_page_status_code,
        html=row.block_page_html,
    ).model_dump())


@router.get("/captcha-footer")
async def get_captcha_footer_settings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    return ok(CaptchaFooterSettingsOut(
        html=row.captcha_footer_html or DEFAULT_CAPTCHA_FOOTER_HTML,
    ).model_dump())


@router.put("/captcha-footer")
async def update_captcha_footer_settings(
    body: CaptchaFooterSettings,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    row.captcha_footer_html = body.html
    await db.commit()
    await db.refresh(row)
    await rule_sync.publish(db)
    return ok(CaptchaFooterSettingsOut(html=row.captcha_footer_html).model_dump())


@router.get("/display")
async def get_display_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    if not row.panel_public_url:
        row.panel_public_url = waf_settings.infer_panel_public_url(request)
        await db.commit()
        await db.refresh(row)
    return ok(DisplaySettingsOut.from_row(row, backend_port=settings.backend_port).model_dump())


@router.put("/display")
async def update_display_settings(
    body: DisplaySettings,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await waf_settings.get_or_create(db)
    row.timezone = body.timezone
    row.panel_public_url = body.panel_public_url
    row.acme_account_email = body.acme_account_email
    await db.commit()
    await db.refresh(row)
    return ok(DisplaySettingsOut.from_row(row, backend_port=settings.backend_port).model_dump())
