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
    panel_public_url: str = Field(min_length=8, max_length=512)
    acme_account_email: str | None = Field(default=None, max_length=254)

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        if value not in ALLOWED_TIMEZONES:
            raise ValueError(f"不支持的时区: {value}")
        return value

    @field_validator("panel_public_url")
    @classmethod
    def _validate_panel_public_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("面板地址必须以 http:// 或 https:// 开头")
        return normalized

    @field_validator("acme_account_email", mode="before")
    @classmethod
    def _validate_acme_account_email(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if "@" not in text or "." not in text.rsplit("@", 1)[-1]:
            raise ValueError("ACME 账户邮箱格式无效")
        return text.lower()


class DisplaySettingsOut(DisplaySettings):
    timezone_options: list[TimezoneOption] = Field(
        default_factory=lambda: [TimezoneOption.model_validate(opt) for opt in TIMEZONE_OPTIONS]
    )
    backend_port: int = 8000
    panel_port: int | None = None

    @classmethod
    def from_row(
        cls,
        row,
        *,
        backend_port: int | None = None,
        panel_port: int | None = None,
    ) -> "DisplaySettingsOut":
        from app.services.listen_ports import port_from_url

        tz = getattr(row, "timezone", None) or DEFAULT_TIMEZONE
        if tz not in ALLOWED_TIMEZONES:
            tz = DEFAULT_TIMEZONE
        panel_url = getattr(row, "panel_public_url", None) or ""
        resolved_panel = panel_port if panel_port is not None else port_from_url(panel_url, implicit=False)
        return cls(
            timezone=tz,
            panel_public_url=panel_url,
            acme_account_email=getattr(row, "acme_account_email", None) or None,
            backend_port=backend_port if backend_port is not None else 8000,
            panel_port=resolved_panel,
        )
