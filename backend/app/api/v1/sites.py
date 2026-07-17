from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import Pagination, get_current_user
from app.api.listing import (
    ListQuery,
    apply_enabled_filter,
    apply_q_filter,
    get_list_query,
    order_by_fields,
)
from app.core.db import get_db
from app.models import Certificate, Site, User
from app.schemas.common import ok
from app.schemas.site import SiteCreate, SiteOption, SiteOut, SiteUpdate
from app.constants.response_pages import DEFAULT_BLOCK_PAGE_HTML, DEFAULT_BLOCK_PAGE_STATUS, DEFAULT_CAPTCHA_FOOTER_HTML
from app.services import nginx_conf, rule_sync

router = APIRouter()


async def _sync(db: AsyncSession) -> None:
    await rule_sync.publish(db)
    await nginx_conf.regenerate(db)


def _validate_listen(*, listen_http: bool, listen_https: bool) -> None:
    if not listen_http and not listen_https:
        raise HTTPException(status_code=400, detail="至少需要开启 HTTP 或 HTTPS 监听")


def _validate_https(
    *,
    listen_https: bool,
    certificate_id: int | None,
) -> None:
    if listen_https and not certificate_id:
        raise HTTPException(status_code=400, detail="开启 HTTPS 时必须选择 SSL 证书")


async def _ensure_certificate(db: AsyncSession, certificate_id: int) -> None:
    cert = await db.get(Certificate, certificate_id)
    if cert is None:
        raise HTTPException(status_code=400, detail="所选证书不存在")


def _normalize_response_pages(data: dict) -> None:
    if data.get("custom_block_page_enabled"):
        if data.get("block_page_status_code") is None:
            data["block_page_status_code"] = DEFAULT_BLOCK_PAGE_STATUS
        if not (data.get("block_page_html") or "").strip():
            data["block_page_html"] = DEFAULT_BLOCK_PAGE_HTML
    if data.get("custom_captcha_footer_enabled") and not (data.get("captcha_footer_html") or "").strip():
        data["captcha_footer_html"] = DEFAULT_CAPTCHA_FOOTER_HTML


@router.get("")
async def list_sites(
    pg: Pagination = Depends(),
    query: ListQuery = Depends(get_list_query),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cond = select(Site).options(selectinload(Site.certificate))
    count = select(func.count(Site.id))
    cond = apply_q_filter(cond, query.q, Site.name, Site.domain, Site.origin_host)
    count = apply_q_filter(count, query.q, Site.name, Site.domain, Site.origin_host)
    cond = apply_enabled_filter(cond, Site.enabled, query.enabled)
    count = apply_enabled_filter(count, Site.enabled, query.enabled)
    total = (await db.execute(count)).scalar_one()
    cond = order_by_fields(
        cond,
        query.sort_by,
        query.sort_order,
        {
            "name": Site.name,
            "domain": Site.domain,
            "enabled": Site.enabled,
            "id": Site.id,
        },
        Site.id,
    )
    rows = (
        await db.execute(cond.offset(pg.offset).limit(pg.page_size))
    ).scalars().all()
    return ok({
        "total": total,
        "items": [SiteOut.from_site(r).model_dump() for r in rows],
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.get("/options")
async def site_options(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(select(Site).order_by(Site.name.asc(), Site.id.asc()))
    ).scalars().all()
    return ok([SiteOption.model_validate(r).model_dump() for r in rows])


@router.post("")
async def create_site(
    body: SiteCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    exists = (
        await db.execute(select(Site).where(Site.domain == body.domain))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="该域名已存在")
    _validate_listen(listen_http=body.listen_http, listen_https=body.listen_https)
    _validate_https(listen_https=body.listen_https, certificate_id=body.certificate_id)
    if body.certificate_id:
        await _ensure_certificate(db, body.certificate_id)
    payload = body.model_dump()
    _normalize_response_pages(payload)
    site = Site(**payload)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    await _sync(db)
    return ok(SiteOut.from_site(site).model_dump())


@router.put("/{site_id}")
async def update_site(
    site_id: int,
    body: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    site = await db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="站点不存在")

    data = body.model_dump(exclude_unset=True)
    if "domain" in data and data["domain"] != site.domain:
        exists = (
            await db.execute(select(Site).where(Site.domain == data["domain"]))
        ).scalar_one_or_none()
        if exists is not None:
            raise HTTPException(status_code=400, detail="该域名已存在")
    listen_http = data.get("listen_http", site.listen_http)
    listen_https = data.get("listen_https", site.listen_https)
    certificate_id = data.get("certificate_id", site.certificate_id)
    _validate_listen(listen_http=listen_http, listen_https=listen_https)
    _validate_https(listen_https=listen_https, certificate_id=certificate_id)
    if certificate_id:
        await _ensure_certificate(db, certificate_id)

    merged = {
        "custom_block_page_enabled": site.custom_block_page_enabled,
        "block_page_status_code": site.block_page_status_code,
        "block_page_html": site.block_page_html,
        "custom_captcha_footer_enabled": site.custom_captcha_footer_enabled,
        "captcha_footer_html": site.captcha_footer_html,
    }
    merged.update(data)
    _normalize_response_pages(merged)
    for key in (
        "custom_block_page_enabled",
        "block_page_status_code",
        "block_page_html",
        "custom_captcha_footer_enabled",
        "captcha_footer_html",
    ):
        if key in merged:
            data[key] = merged[key]

    for k, v in data.items():
        setattr(site, k, v)

    if not site.listen_https:
        site.certificate_id = None

    await db.commit()
    await db.refresh(site)
    await _sync(db)
    return ok(SiteOut.from_site(site).model_dump())


@router.delete("/{site_id}")
async def delete_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    site = await db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="站点不存在")
    await db.delete(site)
    await db.commit()
    await _sync(db)
    return ok()
