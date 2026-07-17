from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.mixins import SiteScopeMixin


class IpListBase(SiteScopeMixin):
    list_type: str = "black"
    name: str
    enabled: bool = True
    conditions: dict | None = None
    remark: str | None = None
    expire_at: datetime | None = None


class IpListCreate(IpListBase):
    pass


class IpListUpdate(BaseModel):
    name: str | None = None
    site_ids: list[int] | None = None
    enabled: bool | None = None
    conditions: dict | None = None
    remark: str | None = None
    expire_at: datetime | None = None


class IpListOut(IpListBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
