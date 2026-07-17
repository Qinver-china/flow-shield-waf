import json

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants.clearance_fingerprint import (
    ALLOWED_FINGERPRINT_DIMS,
    DEFAULT_CLEARANCE_FINGERPRINT_DIMS,
    FINGERPRINT_DIMENSION_OPTIONS,
)
from app.constants.display_settings import (
    ALLOWED_TIMEZONES,
    DEFAULT_TIMEZONE,
    TIMEZONE_OPTIONS,
)


class FingerprintDimensionOption(BaseModel):
    key: str
    label: str
    description: str
    required: bool = False


class ChallengeSettings(BaseModel):
    js_challenge_ttl: int = Field(default=1800, ge=60, le=604800)
    captcha_ttl: int = Field(default=1800, ge=60, le=604800)
    clearance_fingerprint_dims: list[str] = Field(
        default_factory=lambda: list(DEFAULT_CLEARANCE_FINGERPRINT_DIMS)
    )

    @field_validator("clearance_fingerprint_dims")
    @classmethod
    def _validate_fingerprint_dims(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("请至少选择一个指纹维度")
        normalized: list[str] = []
        seen: set[str] = set()
        for dim in value:
            if dim not in ALLOWED_FINGERPRINT_DIMS:
                raise ValueError(f"不支持的指纹维度: {dim}")
            if dim in seen:
                continue
            seen.add(dim)
            normalized.append(dim)
        if "ip" not in seen:
            raise ValueError("指纹维度必须包含 IP")
        return normalized


class ChallengeSettingsOut(ChallengeSettings):
    model_config = ConfigDict(from_attributes=True)
    fingerprint_dimension_options: list[FingerprintDimensionOption] = Field(
        default_factory=lambda: [
            FingerprintDimensionOption.model_validate(opt)
            for opt in FINGERPRINT_DIMENSION_OPTIONS
        ]
    )

    @classmethod
    def from_row(cls, row) -> "ChallengeSettingsOut":
        dims = DEFAULT_CLEARANCE_FINGERPRINT_DIMS
        raw = getattr(row, "clearance_fingerprint_dims", None)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list) and parsed:
                    dims = ChallengeSettings(
                        js_challenge_ttl=row.js_challenge_ttl,
                        captcha_ttl=row.captcha_ttl,
                        clearance_fingerprint_dims=parsed,
                    ).clearance_fingerprint_dims
            except (json.JSONDecodeError, ValueError):
                pass
        return cls(
            js_challenge_ttl=row.js_challenge_ttl,
            captcha_ttl=row.captcha_ttl,
            clearance_fingerprint_dims=dims,
        )


class DebugSettings(BaseModel):
    debug_mode: bool = False
    ratelimit_fail_open: bool = True


class DebugSettingsOut(DebugSettings):
    model_config = ConfigDict(from_attributes=True)


class TimezoneOption(BaseModel):
    value: str
    label: str


class DisplaySettings(BaseModel):
    timezone: str = DEFAULT_TIMEZONE

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        if value not in ALLOWED_TIMEZONES:
            raise ValueError(f"不支持的时区: {value}")
        return value


class DisplaySettingsOut(DisplaySettings):
    timezone_options: list[TimezoneOption] = Field(
        default_factory=lambda: [TimezoneOption.model_validate(opt) for opt in TIMEZONE_OPTIONS]
    )

    @classmethod
    def from_row(cls, row) -> "DisplaySettingsOut":
        tz = getattr(row, "timezone", None) or DEFAULT_TIMEZONE
        if tz not in ALLOWED_TIMEZONES:
            tz = DEFAULT_TIMEZONE
        return cls(timezone=tz)
