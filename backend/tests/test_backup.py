"""Backup export/import helpers."""
from app.services.backup import (
    FORMAT_NAME,
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
        "ai_guard",
        "system_settings",
    }


def test_normalize_sections_default_and_filter():
    assert _normalize_sections(None) == [
        "sites",
        "certificates",
        "ip_groups",
        "rules",
        "bots",
        "ai_guard",
        "system_settings",
    ]
    assert _normalize_sections(["bots", "sites"]) == ["sites", "bots"]


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
