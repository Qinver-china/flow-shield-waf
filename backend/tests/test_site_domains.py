import pytest

from app.services.site_domains import (
    apply_domains_to_site,
    normalize_domain_list,
    site_domain_list,
)


class _Site:
    domain = "www.example.com"
    extra_domains = '["example.com"]'


def test_normalize_domain_list_from_text():
    assert normalize_domain_list("www.a.com, b.com\nc.com") == [
        "www.a.com",
        "b.com",
        "c.com",
    ]


def test_normalize_domain_list_deduplicates():
    assert normalize_domain_list(["WWW.A.com", "www.a.com"]) == ["www.a.com"]


def test_normalize_domain_list_allows_wildcard():
    assert normalize_domain_list(["*.zibll.com", "zibll.com"]) == [
        "*.zibll.com",
        "zibll.com",
    ]


def test_normalize_domain_list_rejects_invalid_wildcard():
    with pytest.raises(ValueError, match="通配符"):
        normalize_domain_list(["*zibll.com"])
    with pytest.raises(ValueError, match="通配符"):
        normalize_domain_list(["www.*.zibll.com"])
    with pytest.raises(ValueError, match="通配符"):
        normalize_domain_list(["*."])
    with pytest.raises(ValueError, match="通配符域名格式无效"):
        normalize_domain_list(["*.com"])


def test_apply_domains_to_site_splits_primary_and_extra():
    site = _Site()
    apply_domains_to_site(site, ["www.zibll.top", "zibll.top"])
    assert site.domain == "www.zibll.top"
    assert site.extra_domains == '["zibll.top"]'
    assert site_domain_list(site) == ["www.zibll.top", "zibll.top"]


def test_normalize_domain_list_rejects_empty():
    with pytest.raises(ValueError):
        normalize_domain_list([])
