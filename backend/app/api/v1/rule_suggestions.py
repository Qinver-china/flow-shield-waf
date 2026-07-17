from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.common import ok
from app.services import rule_suggestions

router = APIRouter()


@router.get("")
async def list_rule_suggestions(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = await rule_suggestions.list_suggestions(db)
    return ok([
        {
            "id": r.id,
            "site_id": r.site_id,
            "pattern_json": r.pattern_json,
            "reason": r.reason,
            "sample_request_ids": r.sample_request_ids,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ])


@router.post("/analyze")
async def trigger_analysis(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Legacy endpoint — manual analysis moved to AI Guard."""
    _ = db
    return ok({
        "created": 0,
        "message": "规则建议已迁移至「AI 防护」模块，请在自动防护策略或分析记录中查看。",
        "redirect": "/ai-guard",
    })
