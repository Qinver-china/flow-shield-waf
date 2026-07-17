from pydantic import BaseModel, ConfigDict, Field


class IpGroupBase(BaseModel):
    name: str
    remark: str | None = None
    entries: list[str] = Field(default_factory=list)


class IpGroupCreate(IpGroupBase):
    pass


class IpGroupUpdate(BaseModel):
    name: str | None = None
    remark: str | None = None
    entries: list[str] | None = None


class IpGroupOut(IpGroupBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entry_count: int = 0


class IpGroupOption(BaseModel):
    id: int
    name: str
    entry_count: int


class IpGroupBatchEntries(BaseModel):
    entries: list[str] | None = None
    text: str | None = None
