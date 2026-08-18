from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination, get_current_user
from app.core.db import get_db
from app.models import Rule, User
from app.schemas.ai_guard import AiGuardIncidentOut, ApplyIncidentRequest
from app.schemas.common import ok
from app.services.ai_guard.defense.pipeline import (
    apply_incident_rule,
    dismiss_incident,
    expire_stale_suggested_incidents,
    rollback_incident,
)
from app.services.ai_guard.incident_action_html import render_action_page
from app.services.ai_guard.incident_action_tokens import decode_incident_action_token
from app.services.analytics.incident_store import IncidentStore

router = APIRouter()
_incidents = IncidentStore()


def _incident_out(rec, *, applied_rule_exists: bool = False) -> dict:
    return AiGuardIncidentOut(
        id=rec.incident_id,
        policy_id=rec.policy_id,
        site_id=rec.site_id,
        status=rec.status,
        trigger_snapshot=rec.trigger_snapshot,
        log_sample_meta=rec.log_sample_meta,
        analysis_report=rec.analysis_report,
        suggested_rule=rec.suggested_rule,
        applied_rule_id=rec.applied_rule_id,
        applied_rule_exists=applied_rule_exists,
        apply_mode=rec.apply_mode,
        error_detail=rec.error_detail,
        created_at=rec.created_at,
    ).model_dump()


def _decode_action_token(token: str, expected_action: str) -> int:
    try:
        payload = decode_incident_action_token(token)
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=400, detail="链接已过期，请在面板中手动操作") from exc
    except (InvalidTokenError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="链接无效或已损坏") from exc
    if payload["action"] != expected_action:
        raise HTTPException(status_code=400, detail="链接与操作不匹配")
    return int(payload["incident_id"])


@router.get("/actions/apply", response_class=HTMLResponse, include_in_schema=False)
async def apply_incident_via_token(
    token: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
):
    try:
        incident_id = _decode_action_token(token, "apply")
    except HTTPException as exc:
        return HTMLResponse(
            render_action_page(title="无法应用", message=str(exc.detail), success=False),
            status_code=exc.status_code,
        )
    try:
        row = await apply_incident_rule(db, incident_id)
    except ValueError as exc:
        return HTMLResponse(
            render_action_page(title="应用失败", message=str(exc), success=False),
            status_code=400,
        )
    if not row.applied_rule_id:
        return HTMLResponse(
            render_action_page(title="应用失败", message="规则未能创建", success=False),
            status_code=400,
        )
    rule_name = (row.suggested_rule or {}).get("name") or f"规则 #{row.applied_rule_id}"
    return HTMLResponse(
        render_action_page(
            title="规则已应用",
            message=(
                f"事件 #{incident_id} 的建议规则「{rule_name}」已成功创建"
                f"（规则 #{row.applied_rule_id}）。"
            ),
            success=True,
        )
    )


@router.get("/actions/dismiss", response_class=HTMLResponse, include_in_schema=False)
async def dismiss_incident_via_token(
    token: str = Query(..., min_length=10),
):
    try:
        incident_id = _decode_action_token(token, "dismiss")
    except HTTPException as exc:
        return HTMLResponse(
            render_action_page(title="无法忽略", message=str(exc.detail), success=False),
            status_code=exc.status_code,
        )
    try:
        await dismiss_incident(incident_id)
    except ValueError as exc:
        return HTMLResponse(
            render_action_page(title="操作失败", message=str(exc), success=False),
            status_code=400,
        )
    return HTMLResponse(
        render_action_page(
            title="已忽略",
            message=f"事件 #{incident_id} 的建议已忽略，不会再提示应用。",
            success=True,
        )
    )


@router.get("")
async def list_incidents(
    pg: Pagination = Depends(),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        await expire_stale_suggested_incidents()
    except Exception:  # noqa: BLE001
        pass
    rows, total = await _incidents.list(
        status=status,
        offset=pg.offset,
        limit=pg.page_size,
    )
    rule_ids = {int(r.applied_rule_id) for r in rows if r.applied_rule_id}
    existing_rule_ids: set[int] = set()
    if rule_ids:
        existing_rule_ids = set(
            (await db.execute(select(Rule.id).where(Rule.id.in_(rule_ids)))).scalars().all()
        )
    return ok(
        {
            "total": total,
            "items": [
                _incident_out(
                    r,
                    applied_rule_exists=bool(
                        r.applied_rule_id and r.applied_rule_id in existing_rule_ids
                    ),
                )
                for r in rows
            ],
            "page": pg.page,
            "page_size": pg.page_size,
        }
    )


@router.get("/{incident_id}")
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await _incidents.get(incident_id)
    if row is None:
        raise HTTPException(status_code=404, detail="事件不存在")
    rule_exists = bool(row.applied_rule_id and await db.get(Rule, row.applied_rule_id))
    return ok(_incident_out(row, applied_rule_exists=rule_exists))


@router.post("/{incident_id}/apply")
async def apply_incident(
    incident_id: int,
    body: ApplyIncidentRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        row = await apply_incident_rule(db, incident_id, apply_mode=body.apply_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(_incident_out(row, applied_rule_exists=bool(row.applied_rule_id)))


@router.post("/{incident_id}/dismiss")
async def dismiss_incident_route(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        await dismiss_incident(incident_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ok()


@router.post("/{incident_id}/rollback")
async def rollback_incident_rule(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        row = await rollback_incident(db, incident_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(_incident_out(row))
