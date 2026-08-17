from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination, get_current_user
from app.api.listing import (
    ListQuery,
    apply_cert_expiry_filter,
    apply_q_filter,
    get_list_query,
    order_by_fields,
)
from app.core.db import SessionLocal, get_db
from app.models import Certificate, Site, User
from app.models.notification import NotificationChannel
from app.schemas.certificate import (
    AcmeIssueRequest,
    CertificateBoundSite,
    CertificateCreate,
    CertificateDetail,
    CertificateOption,
    CertificateOut,
    CertificateUpdate,
)
from app.schemas.common import ok
from app.services import certificate_store
from app.services.acme_issue import AcmeIssueError, issue_for_site
from app.services.certificate_ops import (
    apply_pem_to_certificate,
    persist_new_certificate,
    reload_sites_using_certificate,
)

router = APIRouter()


def _parse_form_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_form_channel_ids(value: str | list[int] | None) -> list[int]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [int(v) for v in value]
    raw = str(value).strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="通知通道参数格式无效") from exc
    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="通知通道参数格式无效")
    try:
        return [int(v) for v in parsed]
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="通知通道参数格式无效") from exc


def _validate_notify_settings(*, enabled: bool, channel_ids: list[int] | None) -> None:
    if enabled and not channel_ids:
        raise HTTPException(status_code=400, detail="启用到期前通知时请选择通知通道")


def _parse_form_renew_domains(value: str | list[str] | None) -> list[str] | None:
    if value is None or value == "":
        return None
    if isinstance(value, list):
        return [str(v) for v in value]
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="续期域名参数格式无效") from exc
    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="续期域名参数格式无效")
    return [str(v) for v in parsed]


def _apply_acme_renew_settings(
    cert: Certificate,
    *,
    acme_auto_renew: bool | None = None,
    acme_provider: str | None = None,
    renew_domains: list[str] | None = None,
    provider_provided: bool = False,
    renew_domains_provided: bool = False,
) -> None:
    if acme_auto_renew is not None:
        cert.acme_auto_renew = bool(acme_auto_renew)
    if provider_provided:
        cert.acme_provider = acme_provider
    if renew_domains_provided and renew_domains is not None:
        cert.domains = ",".join(renew_domains) if renew_domains else None

    if not cert.acme_auto_renew:
        return
    if not cert.acme_provider:
        raise HTTPException(status_code=400, detail="开启自动续期时请选择证书机构")
    names = [n.strip() for n in (cert.domains or "").split(",") if n.strip()]
    if not names:
        raise HTTPException(status_code=400, detail="开启自动续期时请选择绑定域名")


async def _ensure_notify_channels(db: AsyncSession, channel_ids: list[int]) -> None:
    if not channel_ids:
        return
    unique_ids = list(dict.fromkeys(channel_ids))
    cnt = (
        await db.execute(
            select(func.count()).select_from(NotificationChannel).where(
                NotificationChannel.id.in_(unique_ids)
            )
        )
    ).scalar_one()
    if cnt != len(unique_ids):
        raise HTTPException(status_code=400, detail="通知通道不存在")


async def _bound_sites_by_cert_ids(
    db: AsyncSession, cert_ids: list[int]
) -> dict[int, list[CertificateBoundSite]]:
    if not cert_ids:
        return {}
    rows = (
        await db.execute(
            select(Site.id, Site.name, Site.certificate_id)
            .where(Site.certificate_id.in_(cert_ids))
            .order_by(Site.name.asc(), Site.id.asc())
        )
    ).all()
    grouped: dict[int, list[CertificateBoundSite]] = defaultdict(list)
    for site_id, site_name, cert_id in rows:
        if cert_id is None:
            continue
        grouped[int(cert_id)].append(
            CertificateBoundSite(id=int(site_id), name=str(site_name))
        )
    return grouped


async def _create_certificate(
    db: AsyncSession,
    *,
    name: str,
    cert_content: str,
    key_content: str,
    remark: str | None,
    expiry_notify_enabled: bool = False,
    expiry_notify_channel_ids: list[int] | None = None,
    acme_auto_renew: bool = False,
    acme_provider: str | None = None,
    renew_domains: list[str] | None = None,
) -> Certificate:
    channel_ids = list(expiry_notify_channel_ids or [])
    _validate_notify_settings(enabled=expiry_notify_enabled, channel_ids=channel_ids)
    if not expiry_notify_enabled and not acme_auto_renew:
        channel_ids = []
    else:
        await _ensure_notify_channels(db, channel_ids)
    if acme_auto_renew:
        if not acme_provider:
            raise HTTPException(status_code=400, detail="开启自动续期时请选择证书机构")
        if not renew_domains:
            raise HTTPException(status_code=400, detail="开启自动续期时请选择绑定域名")

    return await persist_new_certificate(
        db,
        name=name,
        cert_content=cert_content,
        key_content=key_content,
        remark=remark,
        expiry_notify_enabled=expiry_notify_enabled,
        expiry_notify_channel_ids=channel_ids,
        acme_auto_renew=acme_auto_renew,
        acme_provider=acme_provider,
        renew_domains=renew_domains,
        commit=True,
    )


@router.get("")
async def list_certificates(
    pg: Pagination = Depends(),
    query: ListQuery = Depends(get_list_query),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cond = select(Certificate)
    count = select(func.count(Certificate.id))
    cond = apply_q_filter(cond, query.q, Certificate.name, Certificate.domains, Certificate.remark)
    count = apply_q_filter(count, query.q, Certificate.name, Certificate.domains, Certificate.remark)
    cond = apply_cert_expiry_filter(cond, Certificate.not_after, query.expiry)
    count = apply_cert_expiry_filter(count, Certificate.not_after, query.expiry)
    total = (await db.execute(count)).scalar_one()
    cond = order_by_fields(
        cond,
        query.sort_by,
        query.sort_order,
        {
            "name": Certificate.name,
            "not_after": Certificate.not_after,
            "id": Certificate.id,
        },
        Certificate.id,
    )
    rows = (
        await db.execute(cond.offset(pg.offset).limit(pg.page_size))
    ).scalars().all()
    bound_map = await _bound_sites_by_cert_ids(db, [r.id for r in rows])
    items = []
    for row in rows:
        item = CertificateOut.model_validate(row).model_copy(
            update={"bound_sites": bound_map.get(row.id, [])}
        )
        items.append(item.model_dump())
    return ok({
        "total": total,
        "items": items,
        "page": pg.page,
        "page_size": pg.page_size,
    })


@router.get("/options")
async def certificate_options(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(select(Certificate).order_by(Certificate.name.asc()))
    ).scalars().all()
    return ok([
        CertificateOption.model_validate(r).model_dump() for r in rows
    ])


@router.post("/acme/issue")
async def issue_acme_certificate(
    body: AcmeIssueRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    if body.expiry_notify_channel_ids:
        await _ensure_notify_channels(db, body.expiry_notify_channel_ids)
    try:
        cert = await issue_for_site(
            db,
            site_id=body.site_id,
            domains=body.domains,
            provider=body.provider,
            auto_renew=body.auto_renew,
            expiry_notify_enabled=body.expiry_notify_enabled,
            expiry_notify_channel_ids=body.expiry_notify_channel_ids,
            renew_domains=body.renew_domains,
            name=body.name,
            replace_certificate_id=body.replace_certificate_id,
        )
    except AcmeIssueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bound_map = await _bound_sites_by_cert_ids(db, [cert.id])
    return ok(
        CertificateOut.model_validate(cert).model_copy(
            update={"bound_sites": bound_map.get(cert.id, [])}
        ).model_dump()
    )


@router.post("/acme/issue/stream")
async def issue_acme_certificate_stream(
    body: AcmeIssueRequest,
    _user: User = Depends(get_current_user),
):
    """SSE progress log for ACME issue; final event carries the certificate."""
    if body.expiry_notify_channel_ids:
        async with SessionLocal() as db:
            await _ensure_notify_channels(db, body.expiry_notify_channel_ids)

    async def event_gen():
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def on_progress(message: str) -> None:
            await queue.put({"type": "log", "message": message})

        async def run() -> None:
            async with SessionLocal() as db:
                try:
                    cert = await issue_for_site(
                        db,
                        site_id=body.site_id,
                        domains=body.domains,
                        provider=body.provider,
                        auto_renew=body.auto_renew,
                        expiry_notify_enabled=body.expiry_notify_enabled,
                        expiry_notify_channel_ids=body.expiry_notify_channel_ids,
                        renew_domains=body.renew_domains,
                        name=body.name,
                        replace_certificate_id=body.replace_certificate_id,
                        on_progress=on_progress,
                    )
                    bound_map = await _bound_sites_by_cert_ids(db, [cert.id])
                    payload = CertificateOut.model_validate(cert).model_copy(
                        update={"bound_sites": bound_map.get(cert.id, [])}
                    ).model_dump(mode="json")
                    await queue.put({"type": "done", "data": payload})
                except AcmeIssueError as exc:
                    await db.rollback()
                    await queue.put({"type": "error", "message": str(exc)})
                except ValueError as exc:
                    await db.rollback()
                    await queue.put({"type": "error", "message": str(exc)})
                except Exception as exc:  # noqa: BLE001
                    await db.rollback()
                    await queue.put(
                        {"type": "error", "message": f"证书申请失败：{exc}"}
                    )
                finally:
                    await queue.put(None)

        task = asyncio.create_task(run())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        finally:
            await task
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{cert_id}")
async def get_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cert = await db.get(Certificate, cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="证书不存在")
    try:
        cert_content, key_content = certificate_store.read_cert_files(
            cert.cert_path, cert.key_path
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    detail = CertificateDetail.model_validate(cert)
    bound_map = await _bound_sites_by_cert_ids(db, [cert.id])
    return ok(
        detail.model_copy(
            update={
                "cert_content": cert_content,
                "key_content": key_content,
                "bound_sites": bound_map.get(cert.id, []),
            }
        ).model_dump()
    )


@router.post("")
async def create_certificate(
    body: CertificateCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        cert = await _create_certificate(
            db,
            name=body.name,
            cert_content=body.cert_content,
            key_content=body.key_content,
            remark=body.remark,
            expiry_notify_enabled=body.expiry_notify_enabled,
            expiry_notify_channel_ids=body.expiry_notify_channel_ids,
            acme_auto_renew=body.acme_auto_renew,
            acme_provider=body.acme_provider,
            renew_domains=body.renew_domains,
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(CertificateOut.model_validate(cert).model_dump())


@router.post("/upload")
async def upload_certificate(
    name: str = Form(...),
    remark: str | None = Form(None),
    expiry_notify_enabled: str | None = Form(None),
    expiry_notify_channel_ids: str | None = Form(None),
    acme_auto_renew: str | None = Form(None),
    acme_provider: str | None = Form(None),
    renew_domains: str | None = Form(None),
    cert_file: UploadFile = File(...),
    key_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cert_content = (await cert_file.read()).decode("utf-8", errors="replace")
    key_content = (await key_file.read()).decode("utf-8", errors="replace")
    provider = (acme_provider or "").strip().lower() or None
    if provider and provider not in {"letsencrypt", "zerossl"}:
        raise HTTPException(status_code=400, detail="请选择 Let's Encrypt 或 ZeroSSL")
    try:
        cert = await _create_certificate(
            db,
            name=name,
            cert_content=cert_content,
            key_content=key_content,
            remark=remark,
            expiry_notify_enabled=_parse_form_bool(expiry_notify_enabled),
            expiry_notify_channel_ids=_parse_form_channel_ids(expiry_notify_channel_ids),
            acme_auto_renew=_parse_form_bool(acme_auto_renew),
            acme_provider=provider,
            renew_domains=_parse_form_renew_domains(renew_domains),
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(CertificateOut.model_validate(cert).model_dump())


@router.put("/{cert_id}")
async def update_certificate(
    cert_id: int,
    body: CertificateUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cert = await db.get(Certificate, cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="证书不存在")

    data = body.model_dump(exclude_unset=True)
    cert_content = data.pop("cert_content", None)
    key_content = data.pop("key_content", None)
    acme_auto_renew = data.pop("acme_auto_renew", None)
    acme_provider = data.pop("acme_provider", None)
    renew_domains = data.pop("renew_domains", None)
    provider_provided = "acme_provider" in body.model_fields_set
    renew_domains_provided = "renew_domains" in body.model_fields_set

    for k, v in data.items():
        setattr(cert, k, v)

    if cert_content is not None or key_content is not None:
        if not (cert_content and key_content):
            raise HTTPException(status_code=400, detail="更新证书时需同时提供证书和私钥")
        try:
            apply_pem_to_certificate(cert, cert_content, key_content)
        except ValueError as exc:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        _apply_acme_renew_settings(
            cert,
            acme_auto_renew=acme_auto_renew,
            acme_provider=acme_provider,
            renew_domains=renew_domains,
            provider_provided=provider_provided,
            renew_domains_provided=renew_domains_provided,
        )
    except HTTPException:
        await db.rollback()
        raise

    enabled = bool(cert.expiry_notify_enabled)
    auto_renew = bool(getattr(cert, "acme_auto_renew", False))
    channel_ids = list(cert.expiry_notify_channel_ids or [])
    if not enabled and not auto_renew:
        channel_ids = []
        cert.expiry_notify_channel_ids = []
    _validate_notify_settings(enabled=enabled, channel_ids=channel_ids)
    if channel_ids:
        await _ensure_notify_channels(db, channel_ids)
        cert.expiry_notify_channel_ids = channel_ids

    await db.commit()
    await db.refresh(cert)
    await reload_sites_using_certificate(db, cert.id)
    return ok(CertificateOut.model_validate(cert).model_dump())


@router.delete("/{cert_id}")
async def delete_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cert = await db.get(Certificate, cert_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="证书不存在")

    refs = (
        await db.execute(
            select(func.count(Site.id)).where(Site.certificate_id == cert_id)
        )
    ).scalar_one()
    if refs:
        raise HTTPException(status_code=400, detail="该证书正在被站点使用，无法删除")

    certificate_store.remove_cert_files(cert_id)
    await db.delete(cert)
    await db.commit()
    return ok()
