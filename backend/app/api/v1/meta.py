from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.fields import catalog_for_frontend
from app.models import User
from app.models.rule import MODES
from app.schemas.common import ok
from app.services.bot_catalog import category_options
from app.services.logging.types import known_types

router = APIRouter()


def _inject_bot_category_options(catalog: dict, options: list[dict[str, str]]) -> dict:
    out = dict(catalog)
    categories = []
    for group in catalog.get("categories") or []:
        fields = []
        for field in group.get("fields") or []:
            entry = dict(field)
            if entry.get("key") == "bot.category":
                entry["options"] = options
            fields.append(entry)
        categories.append({**group, "fields": fields})
    out["categories"] = categories
    return out


@router.get("/fields")
async def fields(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Field catalog for the condition editor (single source of truth)."""
    catalog = catalog_for_frontend()
    options = await category_options(db)
    return ok(_inject_bot_category_options(catalog, options))


@router.get("/enums")
async def enums(_user: User = Depends(get_current_user)):
    return ok({
        "modes": list(MODES),
        "list_types": ["black", "white"],
        "exception_scopes": ["all", "rules", "ratelimit"],
        "log_types": known_types(),
    })
