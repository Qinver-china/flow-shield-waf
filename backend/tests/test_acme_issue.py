"""ACME HTTP-01 issue validation, renew window, and mocked CA persist."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.schemas.certificate import AcmeIssueRequest, CertificateCreate
from app.services.acme_issue import (
    ACME_DEFAULT_EMAIL_DOMAIN,
    AcmeIssueError,
    RENEW_DAYS_BEFORE,
    ensure_acme_account_email,
    issue_for_site,
    new_acme_account_email,
    normalize_issue_domains,
    renew_one,
    should_attempt_renew,
)
from app.services.notifications.certificate_expiry import days_until_expiry


def test_new_acme_account_email_is_random_and_valid():
    first = new_acme_account_email()
    second = new_acme_account_email()
    suffix = f"@{ACME_DEFAULT_EMAIL_DOMAIN}"
    assert first.startswith("acme-") and first.endswith(suffix)
    assert second.startswith("acme-") and second.endswith(suffix)
    assert first != second
    local = first[: -len(suffix)]
    assert local.split("-", 1)[1]


@pytest.mark.asyncio
async def test_ensure_acme_account_email_keeps_existing():
    db = AsyncMock()
    setting = SimpleNamespace(acme_account_email="ops@example.com")
    assert await ensure_acme_account_email(db, setting) == "ops@example.com"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_acme_account_email_generates_when_empty():
    db = AsyncMock()
    setting = SimpleNamespace(acme_account_email="")
    email = await ensure_acme_account_email(db, setting)
    assert email.endswith(f"@{ACME_DEFAULT_EMAIL_DOMAIN}")
    assert setting.acme_account_email == email
    db.commit.assert_awaited()
    db.refresh.assert_awaited()


def test_normalize_issue_rejects_foreign_domain():
    site = SimpleNamespace(id=1, domain="a.example.com", extra_domains=None)
    with pytest.raises(ValueError, match="不属于该站点"):
        normalize_issue_domains(site, ["other.example.com"])


def test_normalize_issue_rejects_wildcard():
    site = SimpleNamespace(id=1, domain="example.com", extra_domains='["*.example.com"]')
    with pytest.raises(ValueError, match="通配符"):
        normalize_issue_domains(site, ["*.example.com"])


def test_normalize_issue_accepts_site_subset():
    site = SimpleNamespace(
        id=1,
        domain="a.example.com",
        extra_domains='["www.example.com", "b.example.com"]',
    )
    assert normalize_issue_domains(site, ["www.example.com"]) == ["www.example.com"]


def test_renew_window_includes_expired_and_skips_same_day():
    now = datetime(2026, 8, 7, 2, 30, 0)  # 10:30 Shanghai
    soon = datetime(2026, 8, 16, 15, 59, 59)  # 9 days left
    expired = datetime(2026, 8, 1, 15, 59, 59)
    far = datetime(2026, 9, 1, 15, 59, 59)
    assert days_until_expiry(
        not_after_utc=soon, now_utc=now, timezone_name="Asia/Shanghai"
    ) <= RENEW_DAYS_BEFORE
    assert should_attempt_renew(
        auto_renew=True,
        provider="letsencrypt",
        not_after=soon,
        last_attempt_on=None,
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )
    assert should_attempt_renew(
        auto_renew=True,
        provider="letsencrypt",
        not_after=expired,
        last_attempt_on=None,
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )
    assert not should_attempt_renew(
        auto_renew=True,
        provider="letsencrypt",
        not_after=soon,
        last_attempt_on="2026-08-07",
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )
    assert not should_attempt_renew(
        auto_renew=True,
        provider="letsencrypt",
        not_after=far,
        last_attempt_on=None,
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )


def test_renew_skips_before_local_10():
    now = datetime(2026, 8, 7, 1, 0, 0)  # 09:00 Shanghai
    soon = datetime(2026, 8, 10, 15, 59, 59)
    assert not should_attempt_renew(
        auto_renew=True,
        provider="letsencrypt",
        not_after=soon,
        last_attempt_on=None,
        now_utc=now,
        timezone_name="Asia/Shanghai",
    )


def test_auto_renew_does_not_require_notify_channels():
    req = AcmeIssueRequest(
        site_id=1,
        domains=["a.example.com"],
        provider="letsencrypt",
        auto_renew=True,
        expiry_notify_channel_ids=[],
    )
    assert req.auto_renew is True
    assert req.expiry_notify_channel_ids == []
    assert "panel_push_enabled" not in req.model_fields_set
    assert "panel_push_targets" not in req.model_fields_set

    explicit = AcmeIssueRequest(
        site_id=1,
        domains=["a.example.com"],
        provider="letsencrypt",
        auto_renew=True,
        panel_push_enabled=True,
        panel_push_targets=[{"connection_id": 1, "site_keys": ["a.example.com"]}],
    )
    assert "panel_push_enabled" in explicit.model_fields_set
    assert explicit.panel_push_enabled is True

    created = CertificateCreate(
        name="demo",
        cert_content="CERT",
        key_content="KEY",
        acme_auto_renew=True,
        acme_provider="letsencrypt",
        renew_domains=["a.example.com"],
        expiry_notify_channel_ids=[],
    )
    assert created.acme_auto_renew is True
    assert created.expiry_notify_channel_ids == []


def test_expiry_notify_still_requires_channels():
    with pytest.raises(ValidationError, match="启用到期前通知时请选择通知通道"):
        AcmeIssueRequest(
            site_id=1,
            domains=["a.example.com"],
            provider="letsencrypt",
            expiry_notify_enabled=True,
            expiry_notify_channel_ids=[],
        )
    with pytest.raises(ValidationError, match="启用到期前通知时请选择通知通道"):
        CertificateCreate(
            name="demo",
            cert_content="CERT",
            key_content="KEY",
            expiry_notify_enabled=True,
            expiry_notify_channel_ids=[],
        )


@pytest.mark.asyncio
async def test_issue_rejects_notify_without_channels():
    db = AsyncMock()
    with pytest.raises(AcmeIssueError, match="启用到期前通知时请选择通知通道"):
        await issue_for_site(
            db,
            site_id=1,
            domains=["a.example.com"],
            provider="letsencrypt",
            auto_renew=True,
            expiry_notify_enabled=True,
            expiry_notify_channel_ids=[],
        )


@pytest.mark.asyncio
async def test_issue_allows_auto_renew_without_channels():
    site = SimpleNamespace(
        id=1,
        domain="a.example.com",
        extra_domains=None,
        certificate_id=None,
        listen_https=False,
    )
    created = SimpleNamespace(id=9, name="Let's Encrypt · a.example.com", domains="a.example.com")
    db = AsyncMock()
    db.get = AsyncMock(return_value=site)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    with (
        patch(
            "app.services.acme_issue.waf_settings.get_or_create",
            AsyncMock(return_value=SimpleNamespace(acme_account_email="ops@example.com")),
        ),
        patch("app.services.acme_issue.ensure_acme_http_ready", AsyncMock()),
        patch(
            "app.services.acme_issue.request_certificate_pem",
            return_value=("CERT", "KEY"),
        ),
        patch(
            "app.services.acme_issue.persist_new_certificate",
            AsyncMock(return_value=created),
        ),
        patch(
            "app.services.acme_issue.reload_sites_using_certificate",
            AsyncMock(return_value=True),
        ),
        patch(
            "app.services.acme_issue.get_traffic_timezone",
            AsyncMock(return_value="Asia/Shanghai"),
        ),
        patch("app.services.acme_issue.notify_acme_result", AsyncMock()) as notify,
    ):
        cert = await issue_for_site(
            db,
            site_id=1,
            domains=["a.example.com"],
            provider="letsencrypt",
            auto_renew=True,
            expiry_notify_channel_ids=[],
        )
    assert cert is created
    assert created.acme_auto_renew is True
    assert created.expiry_notify_channel_ids == []
    notify.assert_awaited()
    assert notify.await_args.args[1] == []


@pytest.mark.asyncio
async def test_issue_generates_default_email_when_unset():
    site = SimpleNamespace(
        id=1,
        domain="a.example.com",
        extra_domains=None,
        certificate_id=None,
        listen_https=False,
    )
    created = SimpleNamespace(id=9, name="cert", domains="a.example.com")
    setting = SimpleNamespace(acme_account_email=None)
    db = AsyncMock()
    db.get = AsyncMock(return_value=site)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    with (
        patch(
            "app.services.acme_issue.waf_settings.get_or_create",
            AsyncMock(return_value=setting),
        ),
        patch("app.services.acme_issue.ensure_acme_http_ready", AsyncMock()),
        patch(
            "app.services.acme_issue.request_certificate_pem",
            return_value=("CERT", "KEY"),
        ) as request_pem,
        patch(
            "app.services.acme_issue.persist_new_certificate",
            AsyncMock(return_value=created),
        ),
        patch(
            "app.services.acme_issue.reload_sites_using_certificate",
            AsyncMock(return_value=True),
        ),
        patch(
            "app.services.acme_issue.get_traffic_timezone",
            AsyncMock(return_value="Asia/Shanghai"),
        ),
        patch("app.services.acme_issue.notify_acme_result", AsyncMock()),
    ):
        await issue_for_site(
            db,
            site_id=1,
            domains=["a.example.com"],
            provider="letsencrypt",
            auto_renew=False,
            expiry_notify_channel_ids=[],
        )
    assert setting.acme_account_email.endswith(f"@{ACME_DEFAULT_EMAIL_DOMAIN}")
    used_email = request_pem.call_args.args[1]
    assert used_email == setting.acme_account_email


@pytest.mark.asyncio
async def test_issue_for_site_rejects_foreign_domain():
    site = SimpleNamespace(
        id=1, domain="a.example.com", extra_domains=None, certificate_id=None
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=site)
    with (
        patch(
            "app.services.acme_issue.waf_settings.get_or_create",
            AsyncMock(return_value=SimpleNamespace(acme_account_email="ops@example.com")),
        ),
        pytest.raises(AcmeIssueError, match="不属于该站点"),
    ):
        await issue_for_site(
            db,
            site_id=1,
            domains=["other.example.com"],
            provider="letsencrypt",
            auto_renew=False,
            expiry_notify_channel_ids=[],
        )


@pytest.mark.asyncio
async def test_issue_binds_site_and_reloads():
    site = SimpleNamespace(
        id=1,
        domain="a.example.com",
        extra_domains=None,
        certificate_id=None,
        listen_https=False,
    )
    created = SimpleNamespace(id=9, name="Let's Encrypt · a.example.com", domains="a.example.com")
    db = AsyncMock()
    db.get = AsyncMock(return_value=site)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    with (
        patch(
            "app.services.acme_issue.waf_settings.get_or_create",
            AsyncMock(return_value=SimpleNamespace(acme_account_email="ops@example.com")),
        ),
        patch(
            "app.services.acme_issue.ensure_acme_http_ready",
            AsyncMock(),
        ) as ready,
        patch(
            "app.services.acme_issue.request_certificate_pem",
            return_value=("CERT", "KEY"),
        ),
        patch(
            "app.services.acme_issue.persist_new_certificate",
            AsyncMock(return_value=created),
        ) as persist,
        patch("app.services.acme_issue.apply_pem_to_certificate") as apply_pem,
        patch(
            "app.services.acme_issue.reload_sites_using_certificate",
            AsyncMock(return_value=True),
        ) as reload,
        patch(
            "app.services.acme_issue.get_traffic_timezone",
            AsyncMock(return_value="Asia/Shanghai"),
        ),
        patch("app.services.acme_issue.notify_acme_result", AsyncMock()) as notify,
    ):
        cert = await issue_for_site(
            db,
            site_id=1,
            domains=["a.example.com"],
            provider="letsencrypt",
            auto_renew=True,
            expiry_notify_enabled=True,
            expiry_notify_channel_ids=[3],
            renew_domains=["a.example.com", "www.example.com"],
        )
    ready.assert_awaited()
    persist.assert_awaited()
    apply_pem.assert_not_called()
    assert cert is created
    assert created.acme_provider == "letsencrypt"
    assert created.acme_auto_renew is True
    assert created.expiry_notify_enabled is True
    assert created.domains == "a.example.com,www.example.com"
    assert site.certificate_id == 9
    assert site.listen_https is True
    reload.assert_awaited_with(db, 9)
    notify.assert_awaited()
    assert notify.await_args.kwargs["success"] is True


@pytest.mark.asyncio
async def test_issue_failure_notifies_and_does_not_write_cert():
    site = SimpleNamespace(
        id=1,
        domain="a.example.com",
        extra_domains=None,
        certificate_id=None,
        listen_https=False,
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=site)
    with (
        patch(
            "app.services.acme_issue.waf_settings.get_or_create",
            AsyncMock(return_value=SimpleNamespace(acme_account_email="ops@example.com")),
        ),
        patch("app.services.acme_issue.ensure_acme_http_ready", AsyncMock()),
        patch(
            "app.services.acme_issue.request_certificate_pem",
            side_effect=AcmeIssueError("HTTP-01 验证失败"),
        ),
        patch("app.services.acme_issue.persist_new_certificate", AsyncMock()) as persist,
        patch("app.services.acme_issue.apply_pem_to_certificate") as apply_pem,
        patch("app.services.acme_issue.notify_acme_result", AsyncMock()) as notify,
    ):
        with pytest.raises(AcmeIssueError, match="HTTP-01"):
            await issue_for_site(
                db,
                site_id=1,
                domains=["a.example.com"],
                provider="letsencrypt",
                auto_renew=False,
                expiry_notify_channel_ids=[3],
            )
    persist.assert_not_called()
    apply_pem.assert_not_called()
    notify.assert_awaited()
    assert notify.await_args.kwargs["success"] is False
    assert site.certificate_id is None


@pytest.mark.asyncio
async def test_issue_replace_preserves_channels_when_auto_renew_off():
    from app.models import Certificate, Site

    site = SimpleNamespace(
        id=1,
        domain="a.example.com",
        extra_domains=None,
        certificate_id=5,
        listen_https=True,
    )
    target = SimpleNamespace(
        id=5,
        name="old",
        domains="a.example.com",
        acme_provider="letsencrypt",
        acme_auto_renew=True,
        expiry_notify_channel_ids=[7, 8],
        panel_push_enabled=True,
        panel_push_targets=[{"connection_id": 1, "site_keys": ["a.example.com"]}],
    )

    async def get_side_effect(model, pk):
        if model is Site:
            return site
        if model is Certificate:
            return target
        return None

    db = AsyncMock()
    db.get = AsyncMock(side_effect=get_side_effect)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    with (
        patch(
            "app.services.acme_issue.waf_settings.get_or_create",
            AsyncMock(return_value=SimpleNamespace(acme_account_email="ops@example.com")),
        ),
        patch("app.services.acme_issue.ensure_acme_http_ready", AsyncMock()),
        patch(
            "app.services.acme_issue.request_certificate_pem",
            return_value=("CERT", "KEY"),
        ),
        patch("app.services.acme_issue.apply_pem_to_certificate"),
        patch(
            "app.services.acme_issue.reload_sites_using_certificate",
            AsyncMock(return_value=True),
        ),
        patch(
            "app.services.acme_issue.get_traffic_timezone",
            AsyncMock(return_value="Asia/Shanghai"),
        ),
        patch("app.services.acme_issue.notify_acme_result", AsyncMock()),
    ):
        cert = await issue_for_site(
            db,
            site_id=1,
            domains=["a.example.com"],
            provider="letsencrypt",
            auto_renew=False,
            expiry_notify_channel_ids=[],
            replace_certificate_id=5,
        )
    assert cert is target
    assert target.expiry_notify_channel_ids == [7, 8]
    assert target.acme_auto_renew is False
    assert target.panel_push_enabled is False
    assert target.panel_push_targets == []


@pytest.mark.asyncio
async def test_issue_replace_preserves_panel_push_when_omitted():
    from app.models import Certificate, Site

    site = SimpleNamespace(
        id=1,
        domain="a.example.com",
        extra_domains=None,
        certificate_id=5,
        listen_https=True,
    )
    targets = [{"connection_id": 1, "site_keys": ["a.example.com"]}]
    target = SimpleNamespace(
        id=5,
        name="old",
        domains="a.example.com",
        acme_provider="letsencrypt",
        acme_auto_renew=True,
        expiry_notify_channel_ids=[7, 8],
        panel_push_enabled=True,
        panel_push_targets=targets,
    )

    async def get_side_effect(model, pk):
        if model is Site:
            return site
        if model is Certificate:
            return target
        return None

    db = AsyncMock()
    db.get = AsyncMock(side_effect=get_side_effect)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    with (
        patch(
            "app.services.acme_issue.waf_settings.get_or_create",
            AsyncMock(return_value=SimpleNamespace(acme_account_email="ops@example.com")),
        ),
        patch("app.services.acme_issue.ensure_acme_http_ready", AsyncMock()),
        patch(
            "app.services.acme_issue.request_certificate_pem",
            return_value=("CERT", "KEY"),
        ),
        patch("app.services.acme_issue.apply_pem_to_certificate"),
        patch(
            "app.services.acme_issue.reload_sites_using_certificate",
            AsyncMock(return_value=True),
        ),
        patch(
            "app.services.acme_issue.get_traffic_timezone",
            AsyncMock(return_value="Asia/Shanghai"),
        ),
        patch("app.services.acme_issue.notify_acme_result", AsyncMock()),
    ):
        cert = await issue_for_site(
            db,
            site_id=1,
            domains=["a.example.com"],
            provider="letsencrypt",
            auto_renew=True,
            expiry_notify_channel_ids=[7, 8],
            replace_certificate_id=5,
        )
    assert cert is target
    assert target.panel_push_enabled is True
    assert target.panel_push_targets == targets


def test_existing_account_uses_conflict_location():
    from acme import errors, messages

    err = errors.ConflictError("https://acme.example/acme/acct/1")
    regr = messages.RegistrationResource(body={}, uri=err.location)
    assert regr.uri == "https://acme.example/acme/acct/1"


def test_acme_email_html_does_not_escape_line_breaks_as_text():
    from app.services.notifications.email_templates import build_acme_result_email

    _plain, html_body = build_acme_result_email(
        success=False,
        kind="issue",
        cert_name="demo",
        domains="a.example.com",
        ca_name="Let's Encrypt",
        error="DNS 未指向",
    )
    assert "&lt;br/&gt;" not in html_body
    assert "失败原因：DNS 未指向" in html_body


def test_acme_email_appends_panel_sync_note():
    from app.services.notifications.email_templates import build_acme_result_email

    plain, html_body = build_acme_result_email(
        success=True,
        kind="renew",
        cert_name="demo",
        domains="a.example.com",
        ca_name="Let's Encrypt",
        extra_note="已同步到其他面板：a.example.com",
    )
    assert "已同步到其他面板：a.example.com" in plain
    assert "已同步到其他面板：a.example.com" in html_body


def test_acme_email_without_extra_note_matches_original_copy():
    from app.services.notifications.email_templates import build_acme_result_email

    plain, html_body = build_acme_result_email(
        success=True,
        kind="renew",
        cert_name="demo",
        domains="a.example.com",
        ca_name="Let's Encrypt",
    )
    assert "其他面板" not in plain
    assert "其他面板" not in html_body


def test_panel_push_extra_note_formats_partial_failure():
    from app.services.acme_issue import _panel_push_extra_note

    note = _panel_push_extra_note(
        {
            "pushed": [{"name": "a.com"}],
            "failed": [{"name": "b.com", "reason": "timeout"}],
        }
    )
    assert note == "已同步到其他面板：a.com\n其他面板同步失败：b.com（timeout）"


@pytest.mark.asyncio
async def test_issue_emits_progress_logs():
    site = SimpleNamespace(
        id=1,
        domain="a.example.com",
        extra_domains=None,
        certificate_id=None,
        listen_https=False,
    )
    created = SimpleNamespace(id=9, name="cert", domains="a.example.com")
    db = AsyncMock()
    db.get = AsyncMock(return_value=site)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    logs: list[str] = []

    async def on_progress(msg: str) -> None:
        logs.append(msg)

    with (
        patch(
            "app.services.acme_issue.waf_settings.get_or_create",
            AsyncMock(return_value=SimpleNamespace(acme_account_email="ops@example.com")),
        ),
        patch("app.services.acme_issue.ensure_acme_http_ready", AsyncMock()),
        patch(
            "app.services.acme_issue.request_certificate_pem",
            return_value=("CERT", "KEY"),
        ),
        patch(
            "app.services.acme_issue.persist_new_certificate",
            AsyncMock(return_value=created),
        ),
        patch(
            "app.services.acme_issue.reload_sites_using_certificate",
            AsyncMock(return_value=True),
        ),
        patch(
            "app.services.acme_issue.get_traffic_timezone",
            AsyncMock(return_value="Asia/Shanghai"),
        ),
        patch("app.services.acme_issue.notify_acme_result", AsyncMock()),
    ):
        await issue_for_site(
            db,
            site_id=1,
            domains=["a.example.com"],
            provider="letsencrypt",
            auto_renew=False,
            expiry_notify_channel_ids=[],
            on_progress=on_progress,
        )
    assert any("校验申请参数" in line for line in logs)
    assert any("刷新引擎配置" in line for line in logs)
    assert any("写入证书文件" in line for line in logs)
    assert any("申请完成" in line for line in logs)


def test_panel_push_requires_sites_when_enabled():
    with pytest.raises(ValidationError, match="开启面板推送时请选择要同步的站点"):
        CertificateCreate(
            name="demo",
            cert_content="CERT",
            key_content="KEY",
            acme_auto_renew=True,
            acme_provider="letsencrypt",
            renew_domains=["a.example.com"],
            panel_push_enabled=True,
            panel_push_targets=[],
        )


def test_panel_push_cleared_when_auto_renew_off():
    created = CertificateCreate(
        name="demo",
        cert_content="CERT",
        key_content="KEY",
        acme_auto_renew=False,
        panel_push_enabled=True,
        panel_push_targets=[{"connection_id": 1, "site_keys": ["a.example.com"]}],
    )
    assert created.panel_push_enabled is False
    assert created.panel_push_targets == []


@pytest.mark.asyncio
async def test_renew_one_pushes_to_panels_after_success():
    cert = SimpleNamespace(
        id=3,
        name="demo",
        domains="a.example.com",
        acme_provider="letsencrypt",
        expiry_notify_channel_ids=[4],
        panel_push_enabled=True,
        panel_push_targets=[{"connection_id": 1, "site_keys": ["a.example.com"]}],
        acme_last_attempt_on=None,
        acme_last_error=None,
    )
    db = AsyncMock()
    db.commit = AsyncMock()
    order: list[str] = []

    def fake_apply(row, *_args, **_kwargs):
        row.domains = "cn.example.com"

    async def fake_push(*_args, **_kwargs):
        order.append("push")
        return {"pushed": [{"key": "a.example.com", "name": "a.example.com"}], "failed": []}

    async def fake_notify(*_args, **_kwargs):
        order.append("notify")

    with (
        patch("app.services.acme_issue.ensure_acme_http_ready", AsyncMock()),
        patch("app.services.acme_issue.request_certificate_pem", return_value=("CERT", "KEY")),
        patch("app.services.acme_issue.apply_pem_to_certificate", side_effect=fake_apply),
        patch(
            "app.services.acme_issue.reload_sites_using_certificate",
            AsyncMock(return_value=True),
        ),
        patch("app.services.acme_issue.notify_acme_result", AsyncMock(side_effect=fake_notify)) as notify,
        patch("app.services.acme_issue.push_certificate_to_panels", AsyncMock(side_effect=fake_push)) as push,
    ):
        ok = await renew_one(
            db, cert, timezone_name="Asia/Shanghai", today="2026-08-18", email="ops@example.com"
        )
    assert ok is True
    assert cert.domains == "a.example.com"
    push.assert_awaited_once()
    notify.assert_awaited_once()
    assert order == ["push", "notify"]
    assert "已同步到其他面板：a.example.com" in (notify.await_args.kwargs.get("extra_note") or "")


@pytest.mark.asyncio
async def test_renew_one_still_succeeds_when_panel_push_fails():
    cert = SimpleNamespace(
        id=3,
        name="demo",
        domains="a.example.com",
        acme_provider="letsencrypt",
        expiry_notify_channel_ids=[4],
        panel_push_enabled=True,
        panel_push_targets=[{"connection_id": 1, "site_keys": ["a.example.com"]}],
        acme_last_attempt_on=None,
        acme_last_error=None,
    )
    db = AsyncMock()
    db.commit = AsyncMock()
    with (
        patch("app.services.acme_issue.ensure_acme_http_ready", AsyncMock()),
        patch("app.services.acme_issue.request_certificate_pem", return_value=("CERT", "KEY")),
        patch("app.services.acme_issue.apply_pem_to_certificate"),
        patch(
            "app.services.acme_issue.reload_sites_using_certificate",
            AsyncMock(return_value=True),
        ),
        patch("app.services.acme_issue.notify_acme_result", AsyncMock()) as notify,
        patch(
            "app.services.acme_issue.push_certificate_to_panels",
            AsyncMock(side_effect=RuntimeError("panel down")),
        ),
    ):
        ok = await renew_one(
            db, cert, timezone_name="Asia/Shanghai", today="2026-08-18", email="ops@example.com"
        )
    assert ok is True
    notify.assert_awaited_once()
    assert notify.await_args.kwargs["success"] is True
    assert "其他面板同步失败：panel down" in (notify.await_args.kwargs.get("extra_note") or "")


@pytest.mark.asyncio
async def test_renew_one_skips_panel_note_when_push_disabled():
    cert = SimpleNamespace(
        id=3,
        name="demo",
        domains="a.example.com",
        acme_provider="letsencrypt",
        expiry_notify_channel_ids=[4],
        panel_push_enabled=False,
        panel_push_targets=[],
        acme_last_attempt_on=None,
        acme_last_error=None,
    )
    db = AsyncMock()
    db.commit = AsyncMock()
    with (
        patch("app.services.acme_issue.ensure_acme_http_ready", AsyncMock()),
        patch("app.services.acme_issue.request_certificate_pem", return_value=("CERT", "KEY")),
        patch("app.services.acme_issue.apply_pem_to_certificate"),
        patch(
            "app.services.acme_issue.reload_sites_using_certificate",
            AsyncMock(return_value=True),
        ),
        patch("app.services.acme_issue.notify_acme_result", AsyncMock()) as notify,
        patch("app.services.acme_issue.push_certificate_to_panels", AsyncMock()) as push,
    ):
        ok = await renew_one(
            db, cert, timezone_name="Asia/Shanghai", today="2026-08-18", email="ops@example.com"
        )
    assert ok is True
    push.assert_not_awaited()
    notify.assert_awaited_once()
    assert notify.await_args.kwargs.get("extra_note") is None
