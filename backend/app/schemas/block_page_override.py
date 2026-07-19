"""Shared block-page override fields for rules, lists, and rate limits."""

from pydantic import BaseModel, Field, field_validator, model_validator

from app.constants.response_pages import (
    ALLOWED_BLOCK_STATUS_CODES,
    DEFAULT_BLOCK_PAGE_HTML,
    DEFAULT_BLOCK_PAGE_STATUS,
)


class BlockPageOverrideMixin(BaseModel):
    custom_block_page_enabled: bool = False
    block_page_status_code: int | None = Field(default=None, ge=400, le=599)
    block_page_html: str | None = None

    @field_validator("block_page_status_code")
    @classmethod
    def _validate_block_status(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value not in ALLOWED_BLOCK_STATUS_CODES:
            allowed = ", ".join(str(code) for code in sorted(ALLOWED_BLOCK_STATUS_CODES))
            raise ValueError(f"不支持的响应状态码，可选：{allowed}")
        return value

    @model_validator(mode="after")
    def _validate_block_page(self) -> "BlockPageOverrideMixin":
        if self.custom_block_page_enabled:
            if self.block_page_status_code is None:
                self.block_page_status_code = DEFAULT_BLOCK_PAGE_STATUS
            if not (self.block_page_html or "").strip():
                self.block_page_html = DEFAULT_BLOCK_PAGE_HTML
        return self
