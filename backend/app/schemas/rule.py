from pydantic import BaseModel, ConfigDict, Field

from app.schemas.block_page_override import BlockPageOverrideMixin
from app.schemas.mixins import SiteScopeMixin


class RuleBase(SiteScopeMixin, BlockPageOverrideMixin):
    name: str
    priority: int = 100
    mode: str = "block"  # observe | block | captcha | js_challenge | slide_captcha
    enabled: bool = True
    conditions: dict | None = None
    remark: str | None = None


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: str | None = None
    site_ids: list[int] | None = None
    priority: int | None = None
    mode: str | None = None
    enabled: bool | None = None
    conditions: dict | None = None
    remark: str | None = None
    custom_block_page_enabled: bool | None = None
    block_page_status_code: int | None = Field(default=None, ge=400, le=599)
    block_page_html: str | None = None


class RuleOut(RuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
