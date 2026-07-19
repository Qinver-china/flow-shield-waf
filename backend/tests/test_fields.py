"""Unit tests for the field catalog + condition validator."""
import pytest

from app.fields import validate_condition
from app.fields.catalog import FIELDS, catalog_for_frontend, field_map


def test_simple_leaf_is_normalized_into_group():
    cond = validate_condition({"field": "ip.src", "op": "eq", "value": "1.2.3.4"})
    assert cond["logic"] == "and"
    assert cond["conditions"][0]["field"] == "ip.src"


def test_group_and_or_ok():
    cond = {
        "logic": "or",
        "conditions": [
            {"field": "http.uri.ext", "op": "in_list", "value": ["php", "asp"]},
            {"field": "http.ua", "op": "regex", "value": "sqlmap"},
        ],
    }
    assert validate_condition(cond) == cond


def test_all_any_aliases_normalized():
    cond = validate_condition(
        {
            "any": [
                {"field": "http.uri.query", "op": "regex", "value": "(?i)<script"},
                {
                    "all": [
                        {"field": "http.method", "op": "eq", "value": "POST"},
                        {"field": "http.body.raw", "op": "regex", "value": "(?i)onerror="},
                    ],
                },
            ],
        }
    )
    assert cond["logic"] == "or"
    assert cond["conditions"][1]["logic"] == "and"
    assert cond["conditions"][1]["conditions"][0]["field"] == "http.method"


def test_empty_condition_allowed():
    assert validate_condition(None) == {"logic": "and", "conditions": []}


def test_unknown_field_rejected():
    with pytest.raises(ValueError):
        validate_condition({"field": "does.not.exist", "op": "eq", "value": "x"})


def test_unsupported_operator_rejected():
    with pytest.raises(ValueError):
        # http.method is enum; regex is not allowed
        validate_condition({"field": "http.method", "op": "regex", "value": "x"})


def test_requires_arg_enforced():
    with pytest.raises(ValueError):
        # http.header needs a sub-key (arg)
        validate_condition({"field": "http.header", "op": "equals", "value": "x"})
    # with arg it's fine
    validate_condition({"field": "http.header", "arg": "User-Agent", "op": "equals", "value": "x"})


def test_between_needs_two_values():
    with pytest.raises(ValueError):
        validate_condition({"field": "http.body.size", "op": "between", "value": [1]})
    validate_condition({"field": "http.body.size", "op": "between", "value": [1, 100]})


def test_no_value_operator_ok():
    validate_condition({"field": "http.cookie", "arg": "sid", "op": "key_exists"})


def test_every_field_has_operators():
    for f in FIELDS:
        assert f["operators"], f["key"]


def test_field_map_unique():
    assert len(field_map()) == len(FIELDS)


def test_catalog_for_frontend_shape():
    cat = catalog_for_frontend()
    assert "categories" in cat and "operators" in cat
    assert all("fields" in c for c in cat["categories"])


def test_enum_fields_expose_options():
    cat = catalog_for_frontend()
    fields = {f["key"]: f for c in cat["categories"] for f in c["fields"]}
    assert fields["http.method"]["options"]
    assert any(o["value"] == "GET" for o in fields["http.method"]["options"])
    assert fields["net.scheme"]["options"]
    assert fields["ip.src.is_private"]["options"] == [
        {"value": "true", "label": "是"},
        {"value": "false", "label": "否"},
    ]
    assert fields["traffic.global"]["compare_modes"]
    assert len(fields["traffic.global"]["options"]) == 6
    assert fields["traffic.site"]["compare_modes"]
    assert len(fields["traffic.site"]["options"]) == 6


def test_traffic_global_condition_ok():
    cond = validate_condition({
        "field": "traffic.global",
        "op": "compare",
        "value": {
            "window_sec": 300,
            "compare": "baseline_gt",
            "percent": 50,
        },
    })
    assert cond["conditions"][0]["value"]["compare"] == "baseline_gt"


def test_traffic_global_absolute_ok():
    validate_condition({
        "field": "traffic.global",
        "op": "compare",
        "value": {"window_sec": 30, "compare": "abs_gt", "threshold": 1000},
    })


def test_traffic_site_condition_ok():
    cond = validate_condition({
        "field": "traffic.site",
        "op": "compare",
        "value": {"window_sec": 60, "compare": "qps_gt", "threshold": 50},
    })
    assert cond["conditions"][0]["field"] == "traffic.site"


def test_traffic_global_qps_ok():
    validate_condition({
        "field": "traffic.global",
        "op": "compare",
        "value": {"window_sec": 10, "compare": "qps_lt", "threshold": 1},
    })


def test_traffic_baseline_short_window_rejected():
    with pytest.raises(ValueError):
        validate_condition({
            "field": "traffic.global",
            "op": "compare",
            "value": {"window_sec": 60, "compare": "baseline_gt", "percent": 50},
        })


def test_traffic_invalid_window_rejected():
    with pytest.raises(ValueError):
        validate_condition({
            "field": "traffic.global",
            "op": "compare",
            "value": {"window_sec": 120, "compare": "abs_gt", "threshold": 1},
        })


def test_contains_accepts_multiple_values():
    cond = validate_condition({
        "field": "http.uri.path",
        "op": "contains",
        "value": ["/admin", "/api"],
    })
    assert cond["conditions"][0]["value"] == ["/admin", "/api"]


def test_ua_family_and_os_fields_exist():
    keys = {f["key"] for f in FIELDS}
    assert "ua.family" in keys
    assert "ua.os" in keys
    cat = catalog_for_frontend()
    fields = {f["key"]: f for c in cat["categories"] for f in c["fields"]}
    assert fields["ua.family"]["options"] == [
        {"value": "browser", "label": "浏览器"},
        {"value": "bot", "label": "Bot"},
    ]
