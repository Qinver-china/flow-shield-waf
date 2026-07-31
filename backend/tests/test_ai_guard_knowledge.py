"""Tests for AI Guard knowledge snapshot and field catalog for LLM."""

from app.constants.traffic_windows import TRAFFIC_BASELINE_MIN_WINDOW_SEC, TRAFFIC_WINDOWS_SEC
from app.fields.catalog import catalog_compact_for_llm
from app.services.ai_guard.context.builder import _defense_knowledge, knowledge_for_defense


def test_catalog_compact_traffic_windows_match_engine():
    catalog = catalog_compact_for_llm()
    traffic = catalog["traffic_value"]
    assert traffic["value"]["window_sec"] == list(TRAFFIC_WINDOWS_SEC)
    assert 86400 not in traffic["value"]["window_sec"]
    assert traffic["baseline_min_window_sec"] == TRAFFIC_BASELINE_MIN_WINDOW_SEC


def test_catalog_compact_traffic_invalid_examples_documented():
    catalog = catalog_compact_for_llm()
    invalid = catalog["traffic_value"]["invalid_field_examples"]
    assert "traffic.global.request_count" in invalid
    assert "traffic.site.request_count" in invalid


def test_catalog_compact_traffic_fields_include_compare_modes():
    catalog = catalog_compact_for_llm()
    fields = {item["key"]: item for item in catalog["fields"]}
    assert fields["traffic.global"]["compare_modes"] == [
        "abs_gt",
        "abs_lt",
        "qps_gt",
        "qps_lt",
        "baseline_gt",
        "baseline_lt",
    ]
    assert fields["traffic.site"]["operators"] == ["compare"]


def test_catalog_compact_system_fields_include_compare_modes():
    catalog = catalog_compact_for_llm()
    fields = {item["key"]: item for item in catalog["fields"]}
    assert fields["system.cpu"]["operators"] == ["compare"]
    assert "container_cpu_gt" in fields["system.cpu"]["compare_modes"]
    assert catalog["system_value"]["value"]["window_sec"] == [60, 300, 1800]


def test_catalog_compact_includes_operator_selection():
    catalog = catalog_compact_for_llm()
    selection = catalog["operator_selection"]
    assert "geo.country" in selection["canonical_examples"]["enum"]["fields"]
    assert "neq" in selection["canonical_examples"]["enum"]["use"]
    assert "not_equals" in selection["canonical_examples"]["enum"]["avoid"]


def test_knowledge_for_defense_exports_rule_fields():
    catalog = catalog_compact_for_llm()
    defense = knowledge_for_defense(catalog)
    assert defense["traffic_value"]["examples"]
    assert defense["system_value"]["examples"]
    assert defense["operator_selection"]["rule"]
    assert any(f["key"] == "traffic.global" for f in defense["fields"])
    assert any(f["key"] == "traffic.origin_global" for f in defense["fields"])
    assert any(f["key"] == "system.cpu" for f in defense["fields"])
    assert defense["operators_by_type"]["traffic"] == ["compare"]
    assert defense["operators_by_type"]["system"] == ["compare"]


def test_defense_knowledge_includes_trigger_types():
    defense = _defense_knowledge()
    types = {item["type"] for item in defense["trigger_types"]}
    assert "traffic.origin_qps_gt" in types
    assert "traffic.origin_abs_gt" in types
    assert "traffic.baseline_gt" in types
    assert "security.block_count" in types
    assert "security.block_rate" in types
    assert "system.container_cpu_gt" in types
    assert "system.host_cpu_gt" in types
    assert "system.load_per_core_gt" not in types
    assert "traffic_intel.anomaly" not in types
    assert "suggest_only" in defense["apply_mode_values"]
    assert any("blacklist" in note for note in defense["rule_generation_notes"])
