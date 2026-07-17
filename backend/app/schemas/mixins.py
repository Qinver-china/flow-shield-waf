from pydantic import BaseModel, Field, field_validator


class SiteScopeMixin(BaseModel):
    site_ids: list[int] = Field(default_factory=list)

    @field_validator("site_ids", mode="before")
    @classmethod
    def _coerce_site_ids(cls, v):
        return [] if v is None else v
