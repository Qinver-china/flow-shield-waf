"""FastAPI application entrypoint."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.internal.slide_captcha import router as slide_captcha_router
from app.api.v1 import api_router
from app.background import run_config_sync_retry, run_crawler_vendored_auto_sync
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.core.redis import get_redis
from app.core.security import hash_password
from app.models import User, WafSetting
from app.services import certificate_store, rule_sync, waf_settings
from app.services.schema_bootstrap import ensure_database_schema

log = logging.getLogger("waf.main")


async def _bootstrap() -> None:
    certificate_store.ensure_cert_dir()
    # Model-driven schema: create missing tables on first boot (no alembic).
    await ensure_database_schema()

    async with SessionLocal() as db:
        existing = (
            await db.execute(select(User).where(User.username == settings.waf_admin_user))
        ).scalar_one_or_none()
        if existing is None:
            db.add(User(
                username=settings.waf_admin_user,
                password_hash=hash_password(settings.waf_admin_password),
                is_active=True,
            ))
            await db.commit()
            log.info("bootstrap admin user created: %s", settings.waf_admin_user)
        await waf_settings.get_or_create(db)
        from app.services.ai_guard.config import get_or_create_setting

        await get_or_create_setting(db)
        from app.services.bootstrap_defaults import ensure_default_policies

        seeded = await ensure_default_policies(db)
        if seeded:
            log.info("bootstrap: seeded %d default policies", seeded)
        from app.services.bootstrap_bot_categories import ensure_builtin_categories

        cat_seeded = await ensure_builtin_categories(db)
        if cat_seeded:
            log.info("bootstrap: seeded %d builtin bot categories", cat_seeded)
        from app.services.bootstrap_bots import ensure_builtin_bots

        bot_seeded = await ensure_builtin_bots(db)
        if bot_seeded:
            log.info("bootstrap: seeded %d builtin bot profiles", bot_seeded)
        from app.services.logging.clickhouse_store import ClickHouseLogStore

        await ClickHouseLogStore().ensure_schema()
        from app.services.logging.clickhouse_patches import ensure_clickhouse_columns

        ensure_clickhouse_columns()
        from app.services.logging.clickhouse_patches import ensure_hourly_mv_state

        ensure_hourly_mv_state()
        from app.services.analytics.clickhouse_schema import ensure_analytics_schema

        await asyncio.to_thread(ensure_analytics_schema)
        from app.services.logging.retention_ttl import apply_log_retention_ttl

        await apply_log_retention_ttl()
        from app.services.slide_captcha.service import warmup

        await asyncio.to_thread(warmup)
        from app.services.crawler_vendored.sync import ensure_vendored_rules

        try:
            await ensure_vendored_rules(db)
        except Exception:  # noqa: BLE001
            log.exception("initial crawler vendored bootstrap failed")
        try:
            await rule_sync.publish(db)
        except Exception:  # noqa: BLE001
            log.exception("initial config publish failed")
            await get_redis().set(rule_sync.DIRTY_KEY, "1")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    await _bootstrap()
    stop = asyncio.Event()
    sync_task = asyncio.create_task(run_config_sync_retry(stop))
    crawler_sync_task = asyncio.create_task(run_crawler_vendored_auto_sync(stop))
    try:
        yield
    finally:
        stop.set()
        await sync_task
        await crawler_sync_task


app = FastAPI(
    title="流盾WAF (Flow Shield WAF) API",
    version="0.1.0",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(slide_captcha_router)


@app.get("/health")
async def health():
    return {"code": 0, "message": "ok", "data": {"status": "healthy"}}


@app.exception_handler(HTTPException)
async def http_exc_handler(_req: Request, exc: HTTPException):
    detail = exc.detail
    if not isinstance(detail, str):
        detail = jsonable_encoder(detail)
        if not isinstance(detail, str):
            detail = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": detail, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_req: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "参数校验失败", "data": jsonable_encoder(exc.errors())},
    )


@app.exception_handler(Exception)
async def unhandled_exc_handler(_req: Request, exc: Exception):
    """Surface unexpected failures with a concrete message for the panel."""
    log.exception("unhandled api error: %s", exc)
    detail = str(exc).strip() or exc.__class__.__name__
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": f"服务器错误：{detail}", "data": None},
    )
