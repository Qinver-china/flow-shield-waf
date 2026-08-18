from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _normalize_acme_provider(value: str | None) -> str | None:
    provider = (value or "").strip().lower()
    if not provider:
        return None
    if provider not in {"letsencrypt", "zerossl"}:
        raise ValueError("请选择 Let's Encrypt 或 ZeroSSL")
    return provider


def _normalize_renew_domains(domains: list[str] | None) -> list[str] | None:
    if domains is None:
        return None
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in domains:
        name = str(item or "").strip().lower().rstrip(".")
        if not name or name in seen:
            continue
        seen.add(name)
        cleaned.append(name)
    return cleaned


class PanelPushTarget(BaseModel):
    connection_id: int
    site_keys: list[str] = Field(min_length=1)


def normalize_panel_push_targets(
    targets: list[PanelPushTarget] | list[dict] | None,
) -> list[dict]:
    """Deduplicate connection/site keys for stored panel-push config.

    Args:
        targets: Raw target list from API bodies or stored JSON.

    Returns:
        A list of ``{connection_id, site_keys}`` dicts.

    Raises:
        ValueError: If a target is missing a connection or site keys.
    """
    if not targets:
        return []
    by_connection: dict[int, list[str]] = {}
    seen_keys: dict[int, set[str]] = {}
    for item in targets:
        raw = item.model_dump() if isinstance(item, PanelPushTarget) else item
        if not isinstance(raw, dict):
            raise ValueError("面板推送目标格式无效")
        try:
            connection_id = int(raw.get("connection_id"))
        except (TypeError, ValueError) as exc:
            raise ValueError("请选择要推送的面板账号") from exc
        keys: list[str] = []
        seen = seen_keys.setdefault(connection_id, set())
        for key in raw.get("site_keys") or []:
            site_key = str(key or "").strip()
            if not site_key or site_key in seen:
                continue
            seen.add(site_key)
            keys.append(site_key)
        if not keys:
            raise ValueError("开启面板推送时请选择要同步的站点")
        existing = by_connection.setdefault(connection_id, [])
        existing.extend(keys)
    return [
        {"connection_id": connection_id, "site_keys": keys}
        for connection_id, keys in by_connection.items()
    ]


def apply_panel_push_rules(
    *,
    auto_renew: bool,
    panel_push_enabled: bool,
    panel_push_targets: list[PanelPushTarget] | list[dict] | None,
) -> tuple[bool, list[dict]]:
    """Normalize push flags against auto-renew. Disabled renew clears targets.

    Args:
        auto_renew: Whether ACME auto-renew is on.
        panel_push_enabled: Requested push switch.
        panel_push_targets: Requested panel sites.

    Returns:
        ``(enabled, targets)`` ready to persist.

    Raises:
        ValueError: If push is on without auto-renew or without sites.
    """
    if not auto_renew:
        return False, []
    targets = normalize_panel_push_targets(panel_push_targets)
    if panel_push_enabled and not targets:
        raise ValueError("开启面板推送时请选择要同步的站点")
    if not panel_push_enabled:
        return False, []
    return True, targets


class CertificateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    cert_content: str = Field(min_length=1)
    key_content: str = Field(min_length=1)
    remark: str | None = None
    expiry_notify_enabled: bool = False
    expiry_notify_channel_ids: list[int] = Field(default_factory=list)
    acme_auto_renew: bool = False
    acme_provider: str | None = None
    renew_domains: list[str] | None = None
    panel_push_enabled: bool = False
    panel_push_targets: list[PanelPushTarget] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_notify_and_renew(self) -> "CertificateCreate":
        if self.expiry_notify_enabled and not self.expiry_notify_channel_ids:
            raise ValueError("启用到期前通知时请选择通知通道")
        self.acme_provider = _normalize_acme_provider(self.acme_provider)
        self.renew_domains = _normalize_renew_domains(self.renew_domains)
        if self.acme_auto_renew:
            if not self.acme_provider:
                raise ValueError("开启自动续期时请选择证书机构")
            if not self.renew_domains:
                raise ValueError("开启自动续期时请选择绑定域名")
        enabled, targets = apply_panel_push_rules(
            auto_renew=self.acme_auto_renew,
            panel_push_enabled=self.panel_push_enabled,
            panel_push_targets=self.panel_push_targets,
        )
        self.panel_push_enabled = enabled
        self.panel_push_targets = [PanelPushTarget.model_validate(item) for item in targets]
        return self


class CertificateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    cert_content: str | None = None
    key_content: str | None = None
    remark: str | None = None
    expiry_notify_enabled: bool | None = None
    expiry_notify_channel_ids: list[int] | None = None
    acme_auto_renew: bool | None = None
    acme_provider: str | None = None
    renew_domains: list[str] | None = None
    panel_push_enabled: bool | None = None
    panel_push_targets: list[PanelPushTarget] | None = None

    @model_validator(mode="after")
    def _normalize_acme_fields(self) -> "CertificateUpdate":
        if "acme_provider" in self.model_fields_set:
            self.acme_provider = _normalize_acme_provider(self.acme_provider)
        if "renew_domains" in self.model_fields_set:
            self.renew_domains = _normalize_renew_domains(self.renew_domains)
        if "panel_push_targets" in self.model_fields_set and self.panel_push_targets is not None:
            self.panel_push_targets = [
                PanelPushTarget.model_validate(item)
                for item in normalize_panel_push_targets(self.panel_push_targets)
            ]
        return self


class AcmeIssueRequest(BaseModel):
    site_id: int
    domains: list[str] = Field(min_length=1)
    provider: str
    auto_renew: bool = False
    expiry_notify_enabled: bool = False
    expiry_notify_channel_ids: list[int] = Field(default_factory=list)
    renew_domains: list[str] | None = None
    name: str | None = Field(default=None, max_length=128)
    replace_certificate_id: int | None = None
    panel_push_enabled: bool = False
    panel_push_targets: list[PanelPushTarget] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_acme_issue(self) -> "AcmeIssueRequest":
        provider = (self.provider or "").strip().lower()
        if provider not in {"letsencrypt", "zerossl"}:
            raise ValueError("请选择 Let's Encrypt 或 ZeroSSL")
        self.provider = provider
        self.renew_domains = _normalize_renew_domains(self.renew_domains)
        if self.expiry_notify_enabled and not self.expiry_notify_channel_ids:
            raise ValueError("启用到期前通知时请选择通知通道")
        if self.auto_renew and self.renew_domains is not None and not self.renew_domains:
            raise ValueError("开启自动续期时请选择绑定域名")
        push_specified = (
            "panel_push_enabled" in self.model_fields_set
            or "panel_push_targets" in self.model_fields_set
        )
        if push_specified:
            enabled, targets = apply_panel_push_rules(
                auto_renew=self.auto_renew,
                panel_push_enabled=bool(self.panel_push_enabled),
                panel_push_targets=self.panel_push_targets,
            )
            self.panel_push_enabled = enabled
            self.panel_push_targets = [PanelPushTarget.model_validate(item) for item in targets]
        return self


class CertificatePanelSyncRequest(BaseModel):
    targets: list[PanelPushTarget] | None = None

    @model_validator(mode="after")
    def _normalize_targets(self) -> "CertificatePanelSyncRequest":
        if self.targets is not None:
            self.targets = [
                PanelPushTarget.model_validate(item)
                for item in normalize_panel_push_targets(self.targets)
            ]
        return self


class CertificateBoundSite(BaseModel):
    id: int
    name: str


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    domains: str | None = None
    cert_path: str
    key_path: str
    not_before: datetime | None = None
    not_after: datetime | None = None
    remark: str | None = None
    expiry_notify_enabled: bool = False
    expiry_notify_channel_ids: list[int] = Field(default_factory=list)
    acme_provider: str | None = None
    acme_auto_renew: bool = False
    acme_last_attempt_on: str | None = None
    acme_last_error: str | None = None
    panel_push_enabled: bool = False
    panel_push_targets: list[PanelPushTarget] = Field(default_factory=list)
    bound_sites: list[CertificateBoundSite] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("expiry_notify_channel_ids", mode="before")
    @classmethod
    def _coerce_channel_ids(cls, value: object) -> list:
        return list(value or [])

    @field_validator("panel_push_targets", mode="before")
    @classmethod
    def _coerce_panel_push_targets(cls, value: object) -> list:
        return list(value or [])

    @field_validator("bound_sites", mode="before")
    @classmethod
    def _coerce_bound_sites(cls, value: object) -> list:
        return list(value or [])


class CertificateDetail(CertificateOut):
    cert_content: str = ""
    key_content: str = ""


class CertificateOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    domains: str | None = None
    not_after: datetime | None = None
