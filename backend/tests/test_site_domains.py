import pytest
from pydantic import ValidationError

from app.schemas.site import SiteCreate
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


def test_normalize_domain_list_allows_ipv4():
    assert normalize_domain_list(["192.168.1.1", "10.0.0.8"]) == [
        "192.168.1.1",
        "10.0.0.8",
    ]


def test_normalize_domain_list_allows_ipv6_and_canonicalizes_brackets():
    assert normalize_domain_list(["2001:DB8::1", "[2001:db8::1]"]) == [
        "[2001:db8::1]",
    ]


def test_normalize_domain_list_allows_ip_mixed_with_domain():
    assert normalize_domain_list(["example.com", "127.0.0.1"]) == [
        "example.com",
        "127.0.0.1",
    ]


def test_normalize_domain_list_rejects_invalid_ip_like_values():
    with pytest.raises(ValueError, match="域名或 IP 格式无效"):
        normalize_domain_list(["999.1.1.1"])
    with pytest.raises(ValueError, match="域名或 IP 格式无效"):
        normalize_domain_list(["192.168.1.1/24"])
    with pytest.raises(ValueError, match="域名或 IP 格式无效"):
        normalize_domain_list(["192.168.1.1:8080"])


def test_site_create_accepts_ip_domains():
    site = SiteCreate(
        name="ip-site",
        domains=["192.168.1.1", "2001:DB8::1"],
        origin_host="10.0.0.1",
    )
    assert site.domains == ["192.168.1.1", "[2001:db8::1]"]


def test_site_create_still_rejects_invalid_host():
    with pytest.raises(ValidationError):
        SiteCreate(name="bad", domains=["not_a_host"], origin_host="10.0.0.1")
