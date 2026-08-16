"""Replace-current certificate import from an external panel."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.panels.import_service import import_certificates, preview_certificates
from app.services.panels.types import PanelError, PemPair, RawPanelCert


def _adapter_with_certs(*certs: RawPanelCert) -> AsyncMock:
    adapter = AsyncMock()
    adapter.list_certificates = AsyncMock(return_value=list(certs))
    return adapter


@pytest.mark.asyncio
async def test_preview_replace_allows_matching_domains_only():
    target = SimpleNamespace(id=5, domains="a.example.com, www.example.com")
    matching = RawPanelCert(
        key="match",
        name="match",
        domains=["A.example.com", "www.example.com."],
    )
    other = RawPanelCert(key="other", name="other", domains=["other.example.com"])
    db = AsyncMock()
    db.get = AsyncMock(return_value=target)
    adapter = _adapter_with_certs(matching, other)
    with patch("app.services.panels.import_service.adapter_for", return_value=adapter):
        items = await preview_certificates(
            db, MagicMock(), replace_certificate_id=5
        )
    by_key = {item.key: item for item in items}
    assert by_key["match"].already_imported is False
    assert by_key["match"].skip_reason is None
    assert by_key["other"].skip_reason == "与当前证书域名不一致"


@pytest.mark.asyncio
async def test_preview_replace_missing_target():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    with (
        patch("app.services.panels.import_service.adapter_for", return_value=_adapter_with_certs()),
        pytest.raises(PanelError, match="证书不存在"),
    ):
        await preview_certificates(db, MagicMock(), replace_certificate_id=99)


@pytest.mark.asyncio
async def test_import_replace_overwrites_target_without_creating():
    target = SimpleNamespace(
        id=5, domains="a.example.com", cert_path="/c.pem", key_path="/k.pem"
    )
    pair = PemPair(cert_pem="NEWCERT", key_pem="NEWKEY", name="panel-a")
    db = AsyncMock()
    db.get = AsyncMock(return_value=target)
    adapter = AsyncMock()
    adapter.fetch_cert = AsyncMock(return_value=pair)
    with (
        patch("app.services.panels.import_service.adapter_for", return_value=adapter),
        patch(
            "app.services.panels.import_service.certificate_store.validate_pem_pair",
            return_value=(MagicMock(), MagicMock()),
        ),
        patch(
            "app.services.panels.import_service.certificate_store.parse_cert_meta",
            return_value={"domains": "a.example.com"},
        ),
        patch(
            "app.services.panels.import_service.leaf_sha256",
            side_effect=["new-digest", "old-digest"],
        ),
        patch(
            "app.services.panels.import_service.certificate_store.read_cert_files",
            return_value=("OLDCERT", "OLDKEY"),
        ),
        patch("app.services.panels.import_service.apply_pem_to_certificate") as apply_pem,
        patch(
            "app.services.panels.import_service.reload_sites_using_certificate",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("app.services.panels.import_service.persist_new_certificate") as persist,
    ):
        result = await import_certificates(
            db, MagicMock(), ["k1"], replace_certificate_id=5
        )
    persist.assert_not_called()
    apply_pem.assert_called_once_with(target, "NEWCERT", "NEWKEY")
    db.commit.assert_awaited()
    assert result.imported[0].certificate_id == 5
    assert result.imported[0].status == "imported"


@pytest.mark.asyncio
async def test_import_replace_skips_unchanged_fingerprint():
    target = SimpleNamespace(
        id=5, domains="a.example.com", cert_path="/c.pem", key_path="/k.pem"
    )
    pair = PemPair(cert_pem="SAME", key_pem="KEY", name="panel-a")
    db = AsyncMock()
    db.get = AsyncMock(return_value=target)
    adapter = AsyncMock()
    adapter.fetch_cert = AsyncMock(return_value=pair)
    with (
        patch("app.services.panels.import_service.adapter_for", return_value=adapter),
        patch(
            "app.services.panels.import_service.certificate_store.validate_pem_pair",
            return_value=(MagicMock(), MagicMock()),
        ),
        patch(
            "app.services.panels.import_service.certificate_store.parse_cert_meta",
            return_value={"domains": "a.example.com"},
        ),
        patch("app.services.panels.import_service.leaf_sha256", return_value="same"),
        patch(
            "app.services.panels.import_service.certificate_store.read_cert_files",
            return_value=("SAME", "KEY"),
        ),
        patch("app.services.panels.import_service.apply_pem_to_certificate") as apply_pem,
        patch("app.services.panels.import_service.persist_new_certificate") as persist,
    ):
        result = await import_certificates(
            db, MagicMock(), ["k1"], replace_certificate_id=5
        )
    persist.assert_not_called()
    apply_pem.assert_not_called()
    db.commit.assert_not_called()
    assert result.skipped[0].reason == "证书内容未变化"
    assert result.skipped[0].certificate_id == 5


@pytest.mark.asyncio
async def test_import_replace_rejects_domain_mismatch():
    target = SimpleNamespace(id=5, domains="a.example.com")
    pair = PemPair(cert_pem="NEWCERT", key_pem="NEWKEY", name="panel-b")
    db = AsyncMock()
    db.get = AsyncMock(return_value=target)
    adapter = AsyncMock()
    adapter.fetch_cert = AsyncMock(return_value=pair)
    with (
        patch("app.services.panels.import_service.adapter_for", return_value=adapter),
        patch(
            "app.services.panels.import_service.certificate_store.validate_pem_pair",
            return_value=(MagicMock(), MagicMock()),
        ),
        patch(
            "app.services.panels.import_service.certificate_store.parse_cert_meta",
            return_value={"domains": "other.example.com"},
        ),
        patch("app.services.panels.import_service.apply_pem_to_certificate") as apply_pem,
        patch("app.services.panels.import_service.persist_new_certificate") as persist,
    ):
        result = await import_certificates(
            db, MagicMock(), ["k1"], replace_certificate_id=5
        )
    persist.assert_not_called()
    apply_pem.assert_not_called()
    assert result.failed[0].reason == "与当前证书域名不一致"


@pytest.mark.asyncio
async def test_import_replace_rejects_multiple_keys():
    with pytest.raises(PanelError, match="只能选择 1 项"):
        await import_certificates(
            AsyncMock(), MagicMock(), ["a", "b"], replace_certificate_id=5
        )
