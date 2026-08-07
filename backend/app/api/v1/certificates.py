from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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
from app.core.db import get_db
from app.models import Certificate, Site, User
from app.models.notification import NotificationChannel
from app.schemas.certificate import (
    CertificateCreate,
    CertificateDetail,
    CertificateOption,
    CertificateOut,
    CertificateUpdate,
)
from app.schemas.common import ok
from app.services import certificate_store, nginx_conf

router = APIRouter()


async def _reload_sites_using(db: AsyncSession, cert_id: int) -> None:
    refs = (
        await db.execute(select(Site.id).where(Site.certificate_id == cert_id))
    ).scalars().all()
    if refs:
        await nginx_conf.regenerate(db)  # soft-fails if engine is down


def _parse_form_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


async def _ensure_notify_channel(db: AsyncSession, channel_id: int | None) -> None:
    if channel_id is None:
        return
    channel = await db.get(NotificationChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=400, detail="通知通道不存在")


def _validate_notify_settings(*, enabled: bool, channel_id: int | None) -> None:
    if enabled and not channel_id:
        raise HTTPException(status_code=400, detail="启用到期前通知时请选择通知通道")


async def _create_certificate(
    db: AsyncSession,
    *,
    name: str,
    cert_content: str,
    key_content: str,
    remark: str | None,
    expiry_notify_enabled: bool = False,
    expiry_notify_channel_id: int | None = None,
) -> Certificate:
    _validate_notify_settings(
        enabled=expiry_notify_enabled,
        channel_id=expiry_notify_channel_id,
    )
    await _ensure_notify_channel(db, expiry_notify_channel_id)

    cert_obj, _key = certificate_store.validate_pem_pair(cert_content, key_content)
    meta = certificate_store.parse_cert_meta(cert_obj)

    cert = Certificate(
        name=name.strip(),
        domains=meta["domains"],
        cert_path="",
        key_path="",
        not_before=meta["not_before"],
        not_after=meta["not_after"],
        remark=remark,
        expiry_notify_enabled=expiry_notify_enabled,
        expiry_notify_channel_id=expiry_notify_channel_id if expiry_notify_enabled else None,
    )
    db.add(cert)
    await db.flush()

    cert_path, key_path = certificate_store.write_cert_files(
        cert.id, cert_content, key_content
    )
    cert.cert_path = cert_path
    cert.key_path = key_path
    await db.commit()
    await db.refresh(cert)
    return cert


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
    return ok({
        "total": total,
        "items": [CertificateOut.model_validate(r).model_dump() for r in rows],
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
    return ok(
        detail.model_copy(
            update={"cert_content": cert_content, "key_content": key_content}
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
            expiry_notify_channel_id=body.expiry_notify_channel_id,
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
    expiry_notify_channel_id: int | None = Form(None),
    cert_file: UploadFile = File(...),
    key_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cert_content = (await cert_file.read()).decode("utf-8", errors="replace")
    key_content = (await key_file.read()).decode("utf-8", errors="replace")
    try:
        cert = await _create_certificate(
            db,
            name=name,
            cert_content=cert_content,
            key_content=key_content,
            remark=remark,
            expiry_notify_enabled=_parse_form_bool(expiry_notify_enabled),
            expiry_notify_channel_id=expiry_notify_channel_id,
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

    for k, v in data.items():
        setattr(cert, k, v)

    enabled = bool(cert.expiry_notify_enabled)
    channel_id = cert.expiry_notify_channel_id
    _validate_notify_settings(enabled=enabled, channel_id=channel_id)
    if enabled:
        await _ensure_notify_channel(db, channel_id)

    if cert_content is not None or key_content is not None:
        if not (cert_content and key_content):
            raise HTTPException(status_code=400, detail="更新证书时需同时提供证书和私钥")
        try:
            cert_obj, _key = certificate_store.validate_pem_pair(cert_content, key_content)
            meta = certificate_store.parse_cert_meta(cert_obj)
            cert_path, key_path = certificate_store.write_cert_files(
                cert.id, cert_content, key_content
            )
        except ValueError as exc:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        cert.cert_path = cert_path
        cert.key_path = key_path
        cert.domains = meta["domains"]
        cert.not_before = meta["not_before"]
        cert.not_after = meta["not_after"]

    await db.commit()
    await db.refresh(cert)
    await _reload_sites_using(db, cert.id)
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
