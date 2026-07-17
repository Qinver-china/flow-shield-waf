"""Rule validation tests."""

import pytest

from app.fields import validate_condition


def test_non_observe_mode_rejects_empty_conditions():
    with pytest.raises(ValueError, match="条件不能为空"):
        validate_condition({"logic": "and", "conditions": []}, allow_empty=False)


def test_observe_mode_allows_empty_conditions():
    assert validate_condition({"logic": "and", "conditions": []}, allow_empty=True) == {
        "logic": "and",
        "conditions": [],
    }
