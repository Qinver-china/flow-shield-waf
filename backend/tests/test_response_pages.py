"""Tests for default block page / captcha footer templates."""
from app.constants.response_pages import (
    DEFAULT_BLOCK_PAGE_HTML,
    DEFAULT_CAPTCHA_FOOTER_HTML,
    LEGACY_DEFAULT_BLOCK_PAGE_HTML,
    LEGACY_DEFAULT_CAPTCHA_FOOTER_HTML,
    OFFICIAL_SITE_URL,
)


def test_default_pages_link_official_site():
    assert OFFICIAL_SITE_URL == "https://fswaf.top"
    assert f'href="{OFFICIAL_SITE_URL}"' in DEFAULT_BLOCK_PAGE_HTML
    assert "请求被<a href=" in DEFAULT_BLOCK_PAGE_HTML
    assert f'href="{OFFICIAL_SITE_URL}"' in DEFAULT_CAPTCHA_FOOTER_HTML
    assert "{request_id}" in DEFAULT_BLOCK_PAGE_HTML


def test_legacy_defaults_do_not_include_official_site_link():
    assert OFFICIAL_SITE_URL not in LEGACY_DEFAULT_BLOCK_PAGE_HTML
    assert OFFICIAL_SITE_URL not in LEGACY_DEFAULT_CAPTCHA_FOOTER_HTML
    assert "请求被流盾WAF 拦截" in LEGACY_DEFAULT_BLOCK_PAGE_HTML
    assert LEGACY_DEFAULT_CAPTCHA_FOOTER_HTML == "由 <b>流盾WAF</b> · Flow Shield WAF 提供防护"
