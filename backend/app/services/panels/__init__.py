from __future__ import annotations

from typing import Any, Protocol

from app.services.panels.baota import BaotaAdapter
from app.services.panels.onepanel import OnePanelAdapter
from app.services.panels.types import PanelError, PemPair, RawPanelCert, RawPanelSite


class PanelAdapter(Protocol):
    async def test(self) -> str: ...

    async def list_sites(self) -> list[RawPanelSite]: ...

    async def list_certificates(self) -> list[RawPanelCert]: ...

    async def fetch_site_cert(self, site_key: str) -> PemPair | None: ...

    async def fetch_cert(self, cert_key: str) -> PemPair: ...


def get_adapter(
    *,
    provider: str,
    panel_url: str,
    api_key: str,
    verify_tls: bool = False,
    extra: dict[str, Any] | None = None,
) -> PanelAdapter:
    if provider == "baota":
        return BaotaAdapter(
            panel_url=panel_url,
            api_key=api_key,
            verify_tls=verify_tls,
            extra=extra,
        )
    if provider == "onepanel":
        return OnePanelAdapter(
            panel_url=panel_url,
            api_key=api_key,
            verify_tls=verify_tls,
            extra=extra,
        )
    raise PanelError(f"不支持的面板类型：{provider}")
