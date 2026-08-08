"""Configuration backup export / import API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.backup import BackupExportRequest, BackupImportRequest
from app.schemas.common import ok
from app.services import backup as backup_svc

router = APIRouter()


@router.get("/sections")
async def list_sections(_user: User = Depends(get_current_user)):
    return ok(backup_svc.section_catalog())


@router.post("/export")
async def export_backup(
    body: BackupExportRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        payload = await backup_svc.build_export(db, body.sections or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(payload)


@router.post("/import")
async def import_backup(
    body: BackupImportRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        summary = await backup_svc.apply_import(
            db, body.payload, body.sections or None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    msg = "导入完成"
    if not summary.get("engine_synced"):
        msg = summary.get("engine_error") or "导入完成，但引擎同步未完全成功，请检查 WAF 引擎状态"
    return ok(summary, message=msg)
