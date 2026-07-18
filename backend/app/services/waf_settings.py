import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.debug_settings import DEFAULT_DEBUG_MODE
from app.constants.challenge_settings import DEFAULT_CAPTCHA_TTL, DEFAULT_JS_CHALLENGE_TTL
from app.constants.clearance_fingerprint import DEFAULT_CLEARANCE_FINGERPRINT_DIMS
from app.constants.traffic_windows import TRAFFIC_WINDOWS_SEC
from app.constants.logging_settings import (
    DEFAULT_AUTO_THRESHOLDS,
    DEFAULT_LOGGING_AUTO_COOLDOWN_SEC,
    DEFAULT_LOGGING_AUTO_OBSERVE_SAMPLE_RATE,
    DEFAULT_LOGGING_CONTROL_MODE,
    DEFAULT_LOGGING_DETAIL_ON_BLOCK,
    DEFAULT_LOGGING_ENABLED,
    DEFAULT_LOGGING_SKIP_OBSERVE,
    DEFAULT_LOG_RETENTION_DAYS,
    DEFAULT_OBSERVE_SAMPLE_RATE_ACTIVE,
    DEFAULT_OBSERVE_SAMPLE_RATE_IDLE,
)
from app.constants.display_settings import DEFAULT_TIMEZONE
from app.constants.response_pages import (
    DEFAULT_BLOCK_PAGE_HTML,
    DEFAULT_BLOCK_PAGE_STATUS,
    DEFAULT_CAPTCHA_FOOTER_HTML,
)
from app.constants.ratelimit_settings import DEFAULT_RATELIMIT_FAIL_OPEN
from app.models import WafSetting


def normalize_fingerprint_dims(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_CLEARANCE_FINGERPRINT_DIMS)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return list(DEFAULT_CLEARANCE_FINGERPRINT_DIMS)
    if not isinstance(parsed, list) or not parsed:
        return list(DEFAULT_CLEARANCE_FINGERPRINT_DIMS)
    return parsed


async def get_or_create(db: AsyncSession) -> WafSetting:
    row = await db.get(WafSetting, 1)
    if row is None:
        row = WafSetting(
            id=1,
            js_challenge_ttl=DEFAULT_JS_CHALLENGE_TTL,
            captcha_ttl=DEFAULT_CAPTCHA_TTL,
            clearance_fingerprint_dims=json.dumps(
                DEFAULT_CLEARANCE_FINGERPRINT_DIMS, ensure_ascii=False
            ),
            logging_control_mode=DEFAULT_LOGGING_CONTROL_MODE,
            logging_enabled=DEFAULT_LOGGING_ENABLED,
            logging_skip_observe=DEFAULT_LOGGING_SKIP_OBSERVE,
            observe_sample_rate_idle=DEFAULT_OBSERVE_SAMPLE_RATE_IDLE,
            observe_sample_rate_active=DEFAULT_OBSERVE_SAMPLE_RATE_ACTIVE,
            logging_detail_on_block=DEFAULT_LOGGING_DETAIL_ON_BLOCK,
            logging_auto_thresholds=json.dumps(DEFAULT_AUTO_THRESHOLDS, ensure_ascii=False),
            logging_auto_cooldown_sec=DEFAULT_LOGGING_AUTO_COOLDOWN_SEC,
            logging_auto_observe_sample_rate=DEFAULT_LOGGING_AUTO_OBSERVE_SAMPLE_RATE,
            log_retention_days=DEFAULT_LOG_RETENTION_DAYS,
            debug_mode=DEFAULT_DEBUG_MODE,
            ratelimit_fail_open=DEFAULT_RATELIMIT_FAIL_OPEN,
            block_page_status_code=DEFAULT_BLOCK_PAGE_STATUS,
            block_page_html=DEFAULT_BLOCK_PAGE_HTML,
            captcha_footer_html=DEFAULT_CAPTCHA_FOOTER_HTML,
            timezone=DEFAULT_TIMEZONE,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


def normalize_auto_thresholds(raw: str | None) -> list[dict]:
    defaults_by_sec = {
        int(t["window_sec"]): dict(t) for t in DEFAULT_AUTO_THRESHOLDS
    }
    if not raw:
        return list(DEFAULT_AUTO_THRESHOLDS)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return list(DEFAULT_AUTO_THRESHOLDS)
    if not isinstance(parsed, list) or not parsed:
        return list(DEFAULT_AUTO_THRESHOLDS)
    by_sec: dict[int, dict] = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            sec = int(item["window_sec"])
        except (KeyError, TypeError, ValueError):
            continue
        by_sec[sec] = {
            "window_sec": sec,
            "max_requests": int(item["max_requests"]),
        }
    for sec, default in defaults_by_sec.items():
        by_sec.setdefault(sec, dict(default))
    return [by_sec[sec] for sec in TRAFFIC_WINDOWS_SEC if sec in by_sec]


async def get_challenge_settings(db: AsyncSession) -> dict:
    row = await get_or_create(db)
    return {
        "js_challenge_ttl": row.js_challenge_ttl,
        "captcha_ttl": row.captcha_ttl,
        "clearance_fingerprint_dims": normalize_fingerprint_dims(
            row.clearance_fingerprint_dims
        ),
    }


async def get_logging_settings(db: AsyncSession) -> dict:
    row = await get_or_create(db)
    return {
        "logging_control_mode": row.logging_control_mode or DEFAULT_LOGGING_CONTROL_MODE,
        "logging_enabled": bool(row.logging_enabled),
        "logging_skip_observe": bool(row.logging_skip_observe),
        "observe_sample_rate_idle": float(row.observe_sample_rate_idle),
        "observe_sample_rate_active": float(row.observe_sample_rate_active),
        "logging_detail_on_block": bool(row.logging_detail_on_block),
        "logging_auto_thresholds": normalize_auto_thresholds(row.logging_auto_thresholds),
        "logging_auto_cooldown_sec": int(row.logging_auto_cooldown_sec),
        "logging_auto_observe_sample_rate": float(row.logging_auto_observe_sample_rate),
        "log_retention_days": int(row.log_retention_days or DEFAULT_LOG_RETENTION_DAYS),
    }


async def get_block_page_settings(db: AsyncSession) -> dict:
    row = await get_or_create(db)
    return {
        "status_code": row.block_page_status_code or DEFAULT_BLOCK_PAGE_STATUS,
        "html": row.block_page_html or DEFAULT_BLOCK_PAGE_HTML,
    }


async def get_captcha_footer_settings(db: AsyncSession) -> dict:
    row = await get_or_create(db)
    return {
        "html": row.captcha_footer_html or DEFAULT_CAPTCHA_FOOTER_HTML,
    }


async def get_runtime_settings(db: AsyncSession) -> dict:
    row = await get_or_create(db)
    return {
        "js_challenge_ttl": row.js_challenge_ttl,
        "captcha_ttl": row.captcha_ttl,
        "clearance_fingerprint_dims": normalize_fingerprint_dims(
            row.clearance_fingerprint_dims
        ),
        "logging": {
            "logging_control_mode": row.logging_control_mode or DEFAULT_LOGGING_CONTROL_MODE,
            "logging_enabled": bool(row.logging_enabled),
            "logging_skip_observe": bool(row.logging_skip_observe),
            "observe_sample_rate_idle": float(row.observe_sample_rate_idle),
            "observe_sample_rate_active": float(row.observe_sample_rate_active),
            "logging_detail_on_block": bool(row.logging_detail_on_block),
            "logging_auto_thresholds": normalize_auto_thresholds(row.logging_auto_thresholds),
            "logging_auto_cooldown_sec": int(row.logging_auto_cooldown_sec),
            "logging_auto_observe_sample_rate": float(row.logging_auto_observe_sample_rate),
            "log_retention_days": int(row.log_retention_days or DEFAULT_LOG_RETENTION_DAYS),
        },
        "debug_mode": bool(row.debug_mode),
        "ratelimit_fail_open": bool(
            row.ratelimit_fail_open
            if row.ratelimit_fail_open is not None
            else DEFAULT_RATELIMIT_FAIL_OPEN
        ),
        "block_page": {
            "status_code": row.block_page_status_code or DEFAULT_BLOCK_PAGE_STATUS,
            "html": row.block_page_html or DEFAULT_BLOCK_PAGE_HTML,
        },
        "captcha_footer": {
            "html": row.captcha_footer_html or DEFAULT_CAPTCHA_FOOTER_HTML,
        },
    }
