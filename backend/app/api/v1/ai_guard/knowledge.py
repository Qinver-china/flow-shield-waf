from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.common import ok
from app.services.ai_guard.context.builder import build_knowledge_snapshot

router = APIRouter()


@router.get("/snapshot")
async def knowledge_snapshot(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    data = await build_knowledge_snapshot(db)
    return ok(data)
