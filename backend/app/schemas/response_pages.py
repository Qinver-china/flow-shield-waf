from pydantic import BaseModel, Field, field_validator

from app.constants.response_pages import (
    ALLOWED_BLOCK_STATUS_CODES,
    DEFAULT_BLOCK_PAGE_HTML,
    DEFAULT_BLOCK_PAGE_STATUS,
    DEFAULT_CAPTCHA_FOOTER_HTML,
    PAGE_TEMPLATE_VARIABLES,
)


class PageTemplateVariable(BaseModel):
    key: str
    label: str
    description: str


class BlockPageSettings(BaseModel):
    status_code: int = Field(default=DEFAULT_BLOCK_PAGE_STATUS, ge=400, le=599)
    html: str = Field(default=DEFAULT_BLOCK_PAGE_HTML, min_length=1)

    @field_validator("status_code")
    @classmethod
    def _validate_status_code(cls, value: int) -> int:
        if value not in ALLOWED_BLOCK_STATUS_CODES:
            allowed = ", ".join(str(code) for code in sorted(ALLOWED_BLOCK_STATUS_CODES))
            raise ValueError(f"不支持的响应状态码，可选：{allowed}")
        return value


class BlockPageSettingsOut(BlockPageSettings):
    template_variables: list[PageTemplateVariable] = Field(
        default_factory=lambda: [PageTemplateVariable.model_validate(v) for v in PAGE_TEMPLATE_VARIABLES]
    )


class CaptchaFooterSettings(BaseModel):
    html: str = Field(default=DEFAULT_CAPTCHA_FOOTER_HTML, min_length=1)


class CaptchaFooterSettingsOut(CaptchaFooterSettings):
    template_variables: list[PageTemplateVariable] = Field(
        default_factory=lambda: [PageTemplateVariable.model_validate(v) for v in PAGE_TEMPLATE_VARIABLES]
    )
