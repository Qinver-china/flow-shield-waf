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


def test_enum_accepts_string_equality_aliases():
    """geo.country is enum (eq/neq); AI often emits equals/not_equals."""
    cond = validate_condition({
        "logic": "and",
        "conditions": [
            {"field": "geo.country", "op": "not_equals", "value": "CN"},
        ],
    })
    assert cond["conditions"][0]["op"] == "neq"

    cond2 = validate_condition({
        "field": "http.method",
        "op": "equals",
        "value": "POST",
    })
    assert cond2["conditions"][0]["op"] == "eq"


def test_string_accepts_enum_equality_aliases():
    cond = validate_condition({
        "field": "http.uri.path",
        "op": "neq",
        "value": "/admin",
    })
    assert cond["conditions"][0]["op"] == "not_equals"


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


def test_tcp_ip_field_in_catalog():
    fields = field_map()
    assert fields["ip.tcp"]["label"] == "直连 IP"
    assert fields["ip.tcp"]["value_type"] == "ip"
    cond = validate_condition({"field": "ip.tcp", "op": "eq", "value": "203.0.113.10"})
    assert cond["conditions"][0]["field"] == "ip.tcp"


def test_catalog_for_frontend_shape():
    cat = catalog_for_frontend()
    assert "categories" in cat and "operators" in cat
    assert all("fields" in c for c in cat["categories"])


def test_catalog_field_hints():
    cat = catalog_for_frontend()
    fields = {f["key"]: f for c in cat["categories"] for f in c["fields"]}
    assert fields["ip.tcp"]["hint"] == "TCP 连接对端 IP"
    assert fields["http.method"].get("hint") is None
    assert fields["traffic.global"]["hint"] == "全站滑动窗口请求量"
    assert fields["system.cpu"]["hint"] == "容器或宿主机 CPU 使用率"


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
    assert fields["system.cpu"]["compare_modes"]
    assert len(fields["system.cpu"]["options"]) == 3


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


def test_traffic_llm_alias_request_count_normalized():
    cond = validate_condition({
        "field": "traffic.global.request_count",
        "op": "gt",
        "value": 1000,
    })
    leaf = cond["conditions"][0]
    assert leaf["field"] == "traffic.global"
    assert leaf["op"] == "compare"
    assert leaf["value"]["compare"] == "abs_gt"
    assert leaf["value"]["threshold"] == 1000


def test_traffic_llm_alias_qps_normalized():
    cond = validate_condition({
        "field": "traffic.site.qps",
        "op": "gt",
        "value": 50,
    })
    leaf = cond["conditions"][0]
    assert leaf["field"] == "traffic.site"
    assert leaf["value"]["compare"] == "qps_gt"


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


def test_traffic_origin_global_condition_ok():
    cond = validate_condition({
        "field": "traffic.origin_global",
        "op": "compare",
        "value": {"window_sec": 60, "compare": "qps_gt", "threshold": 20},
    })
    assert cond["conditions"][0]["field"] == "traffic.origin_global"


def test_traffic_origin_baseline_rejected():
    with pytest.raises(ValueError, match="回源请求量不支持基线比较"):
        validate_condition({
            "field": "traffic.origin_site",
            "op": "compare",
            "value": {"window_sec": 300, "compare": "baseline_gt", "percent": 50},
        })


def test_traffic_llm_alias_origin_request_count_normalized():
    cond = validate_condition({
        "field": "traffic.origin_global.request_count",
        "op": "gt",
        "value": 500,
    })
    leaf = cond["conditions"][0]
    assert leaf["field"] == "traffic.origin_global"
    assert leaf["value"]["compare"] == "abs_gt"


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
