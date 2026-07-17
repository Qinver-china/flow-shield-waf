from pydantic import BaseModel, ConfigDict, Field

from app.schemas.mixins import SiteScopeMixin


class RuleBase(SiteScopeMixin):
    name: str
    priority: int = 100
    mode: str = "block"  # observe | block | captcha | js_challenge | slide_captcha
    enabled: bool = True
    conditions: dict | None = None


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: str | None = None
    site_ids: list[int] | None = None
    priority: int | None = None
    mode: str | None = None
    enabled: bool | None = None
    conditions: dict | None = None


class RuleOut(RuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
