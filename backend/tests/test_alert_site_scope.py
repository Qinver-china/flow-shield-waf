"""Tests for alert site scope parsing."""
import pytest

from app.constants.alert_site_scope import (
    SITE_SCOPE_ALL,
    SITE_SCOPE_ANY,
    SITE_SCOPE_SINGLE,
    normalize_site_scope_params,
    parse_site_scope,
)
from app.services.notifications.validators import validate_condition_params


def test_normalize_legacy_site_id_only():
    params = normalize_site_scope_params({"site_id": 3, "window_sec": 300})
    assert params["site_scope"] == SITE_SCOPE_SINGLE
    assert params["site_id"] == 3


def test_normalize_empty_is_all():
    params = normalize_site_scope_params({"window_sec": 300})
    assert params["site_scope"] == SITE_SCOPE_ALL
    assert "site_id" not in params


def test_normalize_any_scope():
    params = normalize_site_scope_params({"site_scope": SITE_SCOPE_ANY, "window_sec": 60})
    assert params["site_scope"] == SITE_SCOPE_ANY
    assert "site_id" not in params


def test_parse_site_scope_any():
    scope, site_id = parse_site_scope({"site_scope": SITE_SCOPE_ANY})
    assert scope == SITE_SCOPE_ANY
    assert site_id is None


def test_validate_condition_params_normalizes_site_scope():
    params = validate_condition_params(
        "traffic.abs_gt",
        {"window_sec": 300, "threshold": 100, "site_scope": SITE_SCOPE_ANY},
    )
    assert params["site_scope"] == SITE_SCOPE_ANY


def test_validate_single_requires_site_id():
    with pytest.raises(ValueError, match="必须选择站点"):
        validate_condition_params(
            "traffic.abs_gt",
            {"window_sec": 300, "threshold": 100, "site_scope": SITE_SCOPE_SINGLE},
        )
