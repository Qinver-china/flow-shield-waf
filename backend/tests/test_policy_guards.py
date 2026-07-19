"""Policy guard validation tests."""

import pytest

from app.fields import validate_condition
from app.fields.validator import has_meaningful_conditions


def test_blacklist_rejects_empty_conditions():
    with pytest.raises(ValueError, match="条件不能为空"):
        validate_condition({"logic": "and", "conditions": []}, allow_empty=False)


def test_blacklist_rejects_nested_empty_groups():
    with pytest.raises(ValueError, match="条件不能为空"):
        validate_condition(
            {"logic": "and", "conditions": [{"logic": "or", "conditions": []}]},
            allow_empty=False,
        )


def test_blacklist_accepts_bare_leaf():
    cond = validate_condition(
        {"field": "http.cookie", "op": "exists", "arg": "sid"},
        allow_empty=False,
    )
    assert has_meaningful_conditions(cond)


def test_blacklist_accepts_user_example_format():
    cond = {
        "logic": "and",
        "conditions": [
            {"op": "exists", "arg": "115", "field": "http.cookie"},
            {"op": "is_empty", "field": "http.ua"},
        ],
    }
    assert has_meaningful_conditions(cond)
    validate_condition(cond, allow_empty=False)


def test_exception_all_scope_requires_conditions():
    with pytest.raises(ValueError, match="条件不能为空"):
        validate_condition(None, allow_empty=False)


def test_ratelimit_observe_allows_empty_conditions():
    assert validate_condition(None, allow_empty=True) == {
        "logic": "and",
        "conditions": [],
    }


def test_ratelimit_block_rejects_empty_conditions():
    with pytest.raises(ValueError, match="条件不能为空"):
        validate_condition({"logic": "and", "conditions": []}, allow_empty=False)
