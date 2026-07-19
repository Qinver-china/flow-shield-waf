"""Tests for per-resource block page override schema."""
from app.schemas.block_page_override import BlockPageOverrideMixin


def test_block_page_override_defaults_html_when_enabled():
    row = BlockPageOverrideMixin(custom_block_page_enabled=True)
    assert row.block_page_status_code == 403
    assert row.block_page_html


def test_block_page_override_disabled_skips_html():
    row = BlockPageOverrideMixin(custom_block_page_enabled=False, block_page_html=None)
    assert row.block_page_html is None
