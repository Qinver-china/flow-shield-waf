from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants.bot_settings import DEFAULT_CATEGORY
from app.services.bot_catalog import normalize_patterns


class BotProfileBase(BaseModel):
    name: str
    category: str = DEFAULT_CATEGORY
    ua_patterns: list[str] = Field(default_factory=list)
    enabled: bool = True
    site_ids: list[int] | None = None
    verify_dns_suffix: str | None = None
    remark: str | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("请填写名称")
        if len(name) > 128:
            raise ValueError("名称过长（最多 128 字符）")
        return name

    @field_validator("ua_patterns")
    @classmethod
    def _validate_patterns(cls, value: list[str]) -> list[str]:
        patterns = normalize_patterns(value)
        if not patterns:
            raise ValueError("请至少配置一条 UA 匹配模式")
        return patterns

    @field_validator("verify_dns_suffix")
    @classmethod
    def _validate_dns_suffix(cls, value: str | None) -> str | None:
        if value is None:
            return None
        suffix = value.strip()
        if not suffix:
            return None
        if len(suffix) > 255:
            raise ValueError("DNS 后缀过长（最多 255 字符）")
        return suffix


class BotProfileCreate(BotProfileBase):
    pass


class BotProfileUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    ua_patterns: list[str] | None = None
    enabled: bool | None = None
    site_ids: list[int] | None = None
    verify_dns_suffix: str | None = None
    remark: str | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not name:
            raise ValueError("请填写名称")
        return name

    @field_validator("ua_patterns")
    @classmethod
    def _validate_patterns(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        patterns = normalize_patterns(value)
        if not patterns:
            raise ValueError("请至少配置一条 UA 匹配模式")
        return patterns


class BotProfileOut(BotProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_builtin: bool = False
    pattern_count: int = 0
