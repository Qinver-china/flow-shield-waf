from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.mixins import SiteScopeMixin


class RateLimitKey(BaseModel):
    field: str
    arg: str | None = None


class RateLimitBase(SiteScopeMixin):
    name: str
    priority: int = 100
    enabled: bool = True
    keys: list[RateLimitKey] = Field(default_factory=lambda: [RateLimitKey(field="ip.src")], min_length=1)
    window: int = Field(default=60, ge=1)
    threshold: int = Field(default=100, ge=1)
    mode: str = "block"
    conditions: dict | None = None
    remark: str | None = None


class RateLimitCreate(RateLimitBase):
    pass


class RateLimitUpdate(BaseModel):
    name: str | None = None
    site_ids: list[int] | None = None
    priority: int | None = None
    enabled: bool | None = None
    keys: list[RateLimitKey] | None = Field(default=None, min_length=1)
    window: int | None = Field(default=None, ge=1)
    threshold: int | None = Field(default=None, ge=1)
    mode: str | None = None
    conditions: dict | None = None
    remark: str | None = None


class RateLimitOut(RateLimitBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
