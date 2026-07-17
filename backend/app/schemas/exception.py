from pydantic import BaseModel, ConfigDict, Field

from app.schemas.mixins import SiteScopeMixin


class ExceptionBase(SiteScopeMixin):
    name: str
    scope: str = "all"  # all | rules | ratelimit
    enabled: bool = True
    conditions: dict | None = None
    remark: str | None = None


class ExceptionCreate(ExceptionBase):
    pass


class ExceptionUpdate(BaseModel):
    name: str | None = None
    site_ids: list[int] | None = None
    scope: str | None = None
    enabled: bool | None = None
    conditions: dict | None = None
    remark: str | None = None


class ExceptionOut(ExceptionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
