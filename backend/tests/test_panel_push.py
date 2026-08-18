"""Panel certificate push helpers."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.certificate import apply_panel_push_rules
from app.services.panels.push_service import push_certificate_to_panels
from app.services.panels.types import PanelError


def test_apply_panel_push_rules_requires_sites():
    with pytest.raises(ValueError, match="开启面板推送时请选择要同步的站点"):
        apply_panel_push_rules(auto_renew=True, panel_push_enabled=True, panel_push_targets=[])


def test_apply_panel_push_rules_clears_when_renew_off():
    enabled, targets = apply_panel_push_rules(
        auto_renew=False,
        panel_push_enabled=True,
        panel_push_targets=[{"connection_id": 1, "site_keys": ["a.com"]}],
    )
    assert enabled is False
    assert targets == []


@pytest.mark.asyncio
async def test_push_certificate_reports_missing_connection():
    cert = SimpleNamespace(
        id=1,
        cert_path="c.pem",
        key_path="k.pem",
        panel_push_targets=[{"connection_id": 9, "site_keys": ["a.com"]}],
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    with patch(
        "app.services.panels.push_service.certificate_store.read_cert_files",
        return_value=("CERT", "KEY"),
    ):
        result = await push_certificate_to_panels(db, cert)
    assert result["pushed"] == []
    assert result["failed"][0]["reason"] == "面板账号不存在"


@pytest.mark.asyncio
async def test_push_certificate_requires_targets():
    cert = SimpleNamespace(id=1, cert_path="c.pem", key_path="k.pem", panel_push_targets=[])
    db = AsyncMock()
    with patch(
        "app.services.panels.push_service.certificate_store.read_cert_files",
        return_value=("CERT", "KEY"),
    ):
        with pytest.raises(PanelError, match="请选择要同步的面板站点"):
            await push_certificate_to_panels(db, cert)
