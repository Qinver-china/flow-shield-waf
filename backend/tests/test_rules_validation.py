"""Rule validation tests."""

import pytest

from app.fields import validate_condition
from app.fields.validator import has_meaningful_conditions


def test_non_observe_mode_rejects_empty_conditions():
    with pytest.raises(ValueError, match="条件不能为空"):
        validate_condition({"logic": "and", "conditions": []}, allow_empty=False)


def test_observe_mode_allows_empty_conditions():
    assert validate_condition({"logic": "and", "conditions": []}, allow_empty=True) == {
        "logic": "and",
        "conditions": [],
    }
    assert not has_meaningful_conditions({"logic": "and", "conditions": []})


def test_bare_leaf_counts_as_condition():
    leaf = {"field": "ip.src", "op": "eq", "value": "1.2.3.4"}
    assert has_meaningful_conditions(leaf)
    assert validate_condition(leaf, allow_empty=False)["conditions"][0]["field"] == "ip.src"
