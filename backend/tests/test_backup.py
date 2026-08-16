"""Backup export/import helpers."""
from types import SimpleNamespace

from app.services.backup import (
    FORMAT_NAME,
    _apply_certificate_acme_fields,
    _certificate_domains,
    _normalize_sections,
    _remap_ids,
    _remap_ip_group_ids_in_conditions,
    section_catalog,
)


def test_section_catalog_covers_expected_keys():
    keys = {item["key"] for item in section_catalog()}
    assert keys == {
        "sites",
        "certificates",
        "ip_groups",
        "rules",
        "bots",
        "ai_config",
        "ai_policies",
        "system_settings",
    }
    labels = {item["key"]: item["label"] for item in section_catalog()}
    assert labels["ai_config"] == "AI 配置"
    assert labels["ai_policies"] == "AI 防护策略"
    from app.services.backup import SECTION_DEFS

    assert "panel_connections" in SECTION_DEFS["system_settings"]["bags"]


def test_normalize_sections_default_and_filter():
    assert _normalize_sections(None) == [
        "sites",
        "certificates",
        "ip_groups",
        "rules",
        "bots",
        "ai_config",
        "ai_policies",
        "system_settings",
    ]
    assert _normalize_sections(["bots", "sites"]) == ["sites", "bots"]
    assert _normalize_sections(["ai_guard"]) == ["ai_config", "ai_policies"]


def test_normalize_sections_rejects_unknown():
    try:
        _normalize_sections(["nope"])
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "未知导出分区" in str(exc)


def test_remap_ids_and_conditions():
    assert _remap_ids([1, 2, "3", "x"], {1: 10, 3: 30}) == [10, 30]
    tree = {
        "logic": "and",
        "conditions": [
            {"field": "net.src_ip", "op": "in_ip_group", "value": [7, 8]},
            {"field": "uri.path", "op": "eq", "value": "/"},
        ],
    }
    remapped = _remap_ip_group_ids_in_conditions(tree, {7: 70, 8: 80})
    assert remapped["conditions"][0]["value"] == [70, 80]
    assert remapped["conditions"][1]["value"] == "/"
    assert FORMAT_NAME == "flow-shield-waf-backup"


def test_certificate_domains_prefer_exported_renew_sans():
    assert _certificate_domains({"domains": "a.com,b.com"}, "a.com") == "a.com,b.com"
    assert _certificate_domains({"domains": "  "}, "pem.com") == "pem.com"
    assert _certificate_domains({"domains": None}, "pem.com") == "pem.com"
    assert _certificate_domains({}, "pem.com") == "pem.com"


def test_apply_certificate_acme_fields_from_backup():
    cert = SimpleNamespace(
        acme_provider=None,
        acme_auto_renew=False,
        acme_last_attempt_on=None,
        acme_last_error=None,
    )
    _apply_certificate_acme_fields(
        cert,
        {
            "acme_provider": "letsencrypt",
            "acme_auto_renew": True,
            "acme_last_attempt_on": "2026-08-01",
            "acme_last_error": None,
        },
    )
    assert cert.acme_provider == "letsencrypt"
    assert cert.acme_auto_renew is True
    assert cert.acme_last_attempt_on == "2026-08-01"
    assert cert.acme_last_error is None
