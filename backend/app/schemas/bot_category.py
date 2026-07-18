from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.bot_catalog import validate_category_value


class BotCategoryBase(BaseModel):
    label: str
    sort_order: int = 0
    remark: str | None = None

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str) -> str:
        label = value.strip()
        if not label:
            raise ValueError("请填写显示名称")
        if len(label) > 64:
            raise ValueError("显示名称过长（最多 64 字符）")
        return label


class BotCategoryCreate(BotCategoryBase):
    value: str

    @field_validator("value")
    @classmethod
    def _validate_value(cls, value: str) -> str:
        return validate_category_value(value)


class BotCategoryUpdate(BaseModel):
    label: str | None = None
    sort_order: int | None = None
    remark: str | None = None

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        label = value.strip()
        if not label:
            raise ValueError("请填写显示名称")
        return label


class BotCategoryOut(BotCategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    value: str
    is_builtin: bool = False


class BotCategoryOption(BaseModel):
    value: str
    label: str
