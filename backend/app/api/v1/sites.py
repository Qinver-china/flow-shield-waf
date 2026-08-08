import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.constants.logging_settings import DEFAULT_AUTO_THRESHOLDS
from app.constants.response_pages import DEFAULT_BLOCK_PAGE_HTML, DEFAULT_BLOCK_PAGE_STATUS, DEFAULT_CAPTCHA_FOOTER_HTML
from app.constants.traffic_windows import TRAFFIC_BASELINE_WINDOWS_SEC
from app.core.db import get_db
from app.core.redis import get_redis
from app.models import Certificate, Site, User
from app.schemas.common import ok
from app.schemas.site import SiteCreate, SiteOption, SiteOut, SiteUpdate
from app.services import nginx_conf, rule_sync, waf_settings
from app.services.nginx_conf import format_reload_warn_message
from app.constants.traffic_windows import TRAFFIC_WINDOW_LABELS
from app.services.logging.query_clickhouse import stats_sites_24h_compare
from app.services.traffic_intel.windows import label as traffic_window_label
from app.services.site_domains import apply_domains_to_site, ensure_domains_available
from app.services.traffic_intel.constants import REDIS_SNAPSHOT_KEY
from app.services.traffic_intel.store.baseline_mysql import BaselineStore
from app.services.traffic_intel.timezone import get_traffic_timezone
from app.services.traffic_intel.windows import is_baseline_stable

router = APIRouter()
log = logging.getLogger("waf.api.sites")

SITE_CARD_TRAFFIC_WINDOWS_SEC = (300, 1800, 3600, 86400)


async def _sync(db: AsyncSession):
    """Publish rules and regenerate nginx conf. Returns EngineReloadResult.

    Site rows may already be committed; convert unexpected sync errors into a
    soft-fail result so the panel still gets a concrete reason.
    """
    try:
        await rule_sync.publish(db)
        return await nginx_conf.regenerate(db)
    except Exception as exc:  # noqa: BLE001
        detail = str(exc).strip() or exc.__class__.__name__
        log.exception("site sync failed after commit: %s", detail)
        return nginx_conf.EngineReloadResult(ok=False, reason="engine", detail=detail)


def _reload_warn_message(result) -> str:
    return format_reload_warn_message(result)


def _validate_listen(*, listen_http: bool, listen_https: bool) -> None:
    if not listen_http and not listen_https:
        raise HTTPException(status_code=400, detail="至少需要开启 HTTP 或 HTTPS 监听")


def _validate_https(
    *,
    listen_https: bool,
    certificate_id: int | None,
    force_https: bool = False,
) -> None:
    if listen_https and not certificate_id:
        raise HTTPException(status_code=400, detail="开启 HTTPS 时必须选择 SSL 证书")
    if force_https and not listen_https:
        raise HTTPException(status_code=400, detail="开启强制 HTTPS 需要先开启 HTTPS 监听")


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


@router.get("/metrics")
async def sites_metrics(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Card metrics for site list: 24h security stats + live traffic windows."""
    site_ids = [
        int(r)
        for r in (
            await db.execute(select(Site.id).order_by(Site.id.asc()))
        ).scalars().all()
    ]

    stats_map = await stats_sites_24h_compare(hours=hours)
    logging_cfg = await waf_settings.get_logging_settings(db)
    thresholds = {
        int(t["window_sec"]): int(t["max_requests"])
        for t in logging_cfg.get("logging_auto_thresholds") or DEFAULT_AUTO_THRESHOLDS
    }

    snapshot_raw = await get_redis().get(REDIS_SNAPSHOT_KEY)
    sites_snap: dict = {}
    if snapshot_raw:
        try:
            raw = snapshot_raw.decode("utf-8") if isinstance(snapshot_raw, bytes) else snapshot_raw
            data = json.loads(raw)
            sites_snap = data.get("sites") or {}
        except (json.JSONDecodeError, TypeError, ValueError):
            sites_snap = {}

    timezone_name = await get_traffic_timezone(db)
    baselines = BaselineStore()
    as_of = datetime.utcnow()

    items: dict[str, dict] = {}
    for site_id in site_ids:
        stat = stats_map.get(site_id) or {
            "requests": 0,
            "blocked": 0,
            "unique_ips": 0,
            "requests_delta_pct": None,
            "blocked_delta_pct": None,
            "unique_ips_delta_pct": None,
        }
        site_windows = (sites_snap.get(str(site_id)) or {}).get("windows") or []
        by_sec: dict[int, dict] = {}
        for w in site_windows:
            try:
                by_sec[int(w.get("sec", 0))] = w
            except (TypeError, ValueError):
                continue

        traffic_windows = []
        for sec in SITE_CARD_TRAFFIC_WINDOWS_SEC:
            w = by_sec.get(sec) or {}
            current = int(w.get("requests") or 0)
            qps = (current / sec) if sec > 0 else 0.0
            baseline_avg = None
            baseline_warmup = False
            deviation_ratio = None
            if sec in TRAFFIC_BASELINE_WINDOWS_SEC:
                baseline = await baselines.get(
                    db,
                    site_id=site_id,
                    window_sec=sec,
                    as_of=as_of,
                    timezone_name=timezone_name,
                )
                if baseline is not None and baseline.avg_requests is not None:
                    baseline_avg = round(float(baseline.avg_requests), 1)
                    baseline_warmup = not is_baseline_stable(sec, baseline.sample_count)
                    if baseline.avg_requests > 0:
                        deviation_ratio = round(current / float(baseline.avg_requests), 3)
            traffic_windows.append(
                {
                    "window_sec": sec,
                    "label": traffic_window_label(sec) or TRAFFIC_WINDOW_LABELS.get(sec, f"{sec} 秒"),
                    "requests": current,
                    "qps": qps,
                    "threshold": (
                        w.get("threshold")
                        if w.get("threshold") is not None
                        else thresholds.get(sec)
                    ),
                    "baseline_avg": baseline_avg,
                    "baseline_warmup": baseline_warmup,
                    "deviation_ratio": deviation_ratio,
                    "is_anomaly": False,
                }
            )

        requests = int(stat["requests"] or 0)
        blocked = int(stat["blocked"] or 0)
        items[str(site_id)] = {
            "requests_24h": requests,
            "requests_24h_delta_pct": stat.get("requests_delta_pct"),
            "blocked_24h": blocked,
            "blocked_24h_delta_pct": stat.get("blocked_delta_pct"),
            "unique_ips_24h": int(stat.get("unique_ips") or 0),
            "unique_ips_24h_delta_pct": stat.get("unique_ips_delta_pct"),
            "block_rate": round(blocked * 100 / requests, 1) if requests else 0.0,
            "traffic_windows": traffic_windows,
            "anomaly": False,
            # legacy alias
            "hits_24h": requests,
        }

    return ok({"hours": hours, "items": items})


@router.get("/{site_id}")
async def get_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    site = (
        await db.execute(
            select(Site).options(selectinload(Site.certificate)).where(Site.id == site_id)
        )
    ).scalar_one_or_none()
    if site is None:
        raise HTTPException(status_code=404, detail="站点不存在")
    return ok(SiteOut.from_site(site).model_dump())


@router.post("")
async def create_site(
    body: SiteCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        await ensure_domains_available(db, body.domains)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _validate_listen(listen_http=body.listen_http, listen_https=body.listen_https)
    _validate_https(
        listen_https=body.listen_https,
        certificate_id=body.certificate_id,
        force_https=body.force_https,
    )
    if body.certificate_id:
        await _ensure_certificate(db, body.certificate_id)
    payload = body.model_dump()
    domains = payload.pop("domains")
    _normalize_response_pages(payload)
    site = Site(**payload)
    apply_domains_to_site(site, domains)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    reload_ok = await _sync(db)
    if not reload_ok:
        log.warning("create_site id=%s: engine reload failed after commit", site.id)
        return ok(SiteOut.from_site(site).model_dump(), message=_reload_warn_message(reload_ok))
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
    domains = data.pop("domains", None)
    if domains is not None:
        try:
            await ensure_domains_available(db, domains, exclude_site_id=site.id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    listen_http = data.get("listen_http", site.listen_http)
    listen_https = data.get("listen_https", site.listen_https)
    force_https = data.get("force_https", site.force_https)
    certificate_id = data.get("certificate_id", site.certificate_id)
    _validate_listen(listen_http=listen_http, listen_https=listen_https)
    _validate_https(
        listen_https=listen_https,
        certificate_id=certificate_id,
        force_https=force_https,
    )
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

    if domains is not None:
        apply_domains_to_site(site, domains)

    if not site.listen_https:
        site.certificate_id = None
        site.force_https = False

    await db.commit()
    await db.refresh(site)
    reload_ok = await _sync(db)
    if not reload_ok:
        log.warning("update_site id=%s: engine reload failed after commit", site.id)
        return ok(SiteOut.from_site(site).model_dump(), message=_reload_warn_message(reload_ok))
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
    reload_ok = await _sync(db)
    if not reload_ok:
        log.warning("delete_site id=%s: engine reload failed after commit", site_id)
        return ok(message=_reload_warn_message(reload_ok))
    return ok()
