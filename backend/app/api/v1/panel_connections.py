from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import PanelConnection, User
from app.schemas.common import ok
from app.schemas.panel_connection import (
    API_KEY_MASK,
    PanelConnectionCreate,
    PanelConnectionOut,
    PanelConnectionTestBody,
    PanelConnectionUpdate,
    PanelImportKeys,
)
from app.services.panels import get_adapter
from app.services.panels import import_service
from app.services.panels.mapping import default_origin_host
from app.services.panels.types import PanelError

router = APIRouter()


def _out(row: PanelConnection) -> dict:
    has_key = bool((row.api_key or "").strip())
    data = PanelConnectionOut.model_validate(row).model_dump()
    data["has_api_key"] = has_key
    data["api_key_masked"] = API_KEY_MASK if has_key else None
    if not isinstance(data.get("extra"), dict):
        data["extra"] = {}
    return data


def _http_error(exc: PanelError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _cert_import_error(exc: PanelError) -> HTTPException:
    """Map replace-mode missing certificate to 404; other panel errors stay 400.

    Args:
        exc: Error raised while previewing or importing panel certificates.

    Returns:
        HTTPException with 404 or 400.
    """
    if str(exc) == "证书不存在":
        return HTTPException(status_code=404, detail=str(exc))
    return _http_error(exc)


async def _get_enabled(db: AsyncSession, connection_id: int) -> PanelConnection:
    row = await db.get(PanelConnection, connection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="面板账号不存在")
    if not row.enabled:
        raise HTTPException(status_code=400, detail="该面板账号已停用")
    return row


@router.get("")
async def list_connections(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(select(PanelConnection).order_by(PanelConnection.id.desc()))
    ).scalars().all()
    return ok([_out(r) for r in rows])


@router.post("")
async def create_connection(
    body: PanelConnectionCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = PanelConnection(
        name=body.name,
        provider=body.provider,
        panel_url=body.panel_url,
        api_key=body.api_key or "",
        same_server=body.same_server,
        verify_tls=body.verify_tls,
        enabled=body.enabled,
        remark=body.remark,
        extra=body.extra or {},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok(_out(row))


@router.post("/test")
async def test_unsaved_connection(
    body: PanelConnectionTestBody,
    _user: User = Depends(get_current_user),
):
    if not body.provider or not body.panel_url:
        raise HTTPException(status_code=400, detail="请填写面板类型和地址")
    try:
        adapter = get_adapter(
            provider=body.provider,
            panel_url=body.panel_url,
            api_key=body.api_key or "",
            verify_tls=bool(body.verify_tls),
            extra=body.extra or {},
        )
        message = await adapter.test()
    except PanelError as exc:
        raise _http_error(exc) from exc
    return ok({"ok": True, "message": message})


@router.get("/{connection_id}")
async def get_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(PanelConnection, connection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="面板账号不存在")
    return ok(_out(row))


@router.put("/{connection_id}")
async def update_connection(
    connection_id: int,
    body: PanelConnectionUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(PanelConnection, connection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="面板账号不存在")
    data = body.model_dump(exclude_unset=True)
    api_key = data.pop("api_key", None)
    if api_key is not None and api_key.strip() and api_key.strip() != API_KEY_MASK:
        row.api_key = api_key.strip()
    for key, value in data.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return ok(_out(row))


@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(PanelConnection, connection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="面板账号不存在")
    await db.delete(row)
    await db.commit()
    return ok()


@router.post("/{connection_id}/test")
async def test_connection(
    connection_id: int,
    body: PanelConnectionTestBody | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await db.get(PanelConnection, connection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="面板账号不存在")
    payload = body or PanelConnectionTestBody()
    provider = payload.provider or row.provider
    panel_url = payload.panel_url or row.panel_url
    api_key = payload.api_key
    if not api_key or api_key.strip() in {"", API_KEY_MASK}:
        api_key = row.api_key
    verify_tls = row.verify_tls if payload.verify_tls is None else payload.verify_tls
    extra = payload.extra if payload.extra is not None else (row.extra or {})
    try:
        adapter = get_adapter(
            provider=provider,
            panel_url=panel_url,
            api_key=api_key or "",
            verify_tls=bool(verify_tls),
            extra=extra,
        )
        message = await adapter.test()
    except PanelError as exc:
        raise _http_error(exc) from exc
    return ok({"ok": True, "message": message})


@router.get("/{connection_id}/sites")
async def list_panel_sites(
    connection_id: int,
    purpose: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await _get_enabled(db, connection_id)
    try:
        items = await import_service.preview_sites(db, row, purpose=purpose)
    except PanelError as exc:
        raise _http_error(exc) from exc
    return ok(
        {
            "connection": _out(row),
            "origin_host": default_origin_host(
                row.panel_url, same_server=bool(row.same_server)
            ),
            "items": [item.model_dump() for item in items],
        }
    )


@router.post("/{connection_id}/sites/import")
async def import_panel_sites(
    connection_id: int,
    body: PanelImportKeys,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await _get_enabled(db, connection_id)
    try:
        result = await import_service.import_sites(
            db,
            row,
            body.keys,
            origin_host=body.origin_host,
            origin_http_port=body.origin_http_port,
            origin_https_port=body.origin_https_port,
        )
    except PanelError as exc:
        raise _http_error(exc) from exc
    return ok(result.model_dump(), message=result.warning or "ok")


@router.get("/{connection_id}/certificates")
async def list_panel_certificates(
    connection_id: int,
    replace_certificate_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await _get_enabled(db, connection_id)
    try:
        items = await import_service.preview_certificates(
            db, row, replace_certificate_id=replace_certificate_id
        )
    except PanelError as exc:
        raise _cert_import_error(exc) from exc
    return ok({"connection": _out(row), "items": [item.model_dump() for item in items]})


@router.post("/{connection_id}/certificates/import")
async def import_panel_certificates(
    connection_id: int,
    body: PanelImportKeys,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await _get_enabled(db, connection_id)
    try:
        result = await import_service.import_certificates(
            db, row, body.keys, replace_certificate_id=body.replace_certificate_id
        )
    except PanelError as exc:
        raise _cert_import_error(exc) from exc
    return ok(result.model_dump(), message=result.warning or "ok")
