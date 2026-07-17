"""Policy guard validation tests."""

import pytest

from app.fields import validate_condition


def test_blacklist_rejects_empty_conditions():
    with pytest.raises(ValueError, match="条件不能为空"):
        validate_condition({"logic": "and", "conditions": []}, allow_empty=False)


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
