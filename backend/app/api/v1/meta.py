from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.fields import catalog_for_frontend
from app.models import User
from app.models.rule import MODES
from app.schemas.common import ok
from app.services.logging.types import known_types

router = APIRouter()


@router.get("/fields")
async def fields(_user: User = Depends(get_current_user)):
    """Field catalog for the condition editor (single source of truth)."""
    return ok(catalog_for_frontend())


@router.get("/enums")
async def enums(_user: User = Depends(get_current_user)):
    return ok({
        "modes": list(MODES),
        "list_types": ["black", "white"],
        "exception_scopes": ["all", "rules", "ratelimit"],
        "log_types": known_types(),
    })
