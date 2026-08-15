from types import SimpleNamespace

import pytest

from app.schemas.site import SiteCreate
from app.services.listen_ports import (
    dump_listen_ports,
    parse_listen_ports,
    port_from_url,
    ports_for_db,
    reserved_listen_port_messages,
    validate_cross_site_listen_ports,
    validate_custom_listen_ports,
)
from app.services.nginx_conf import render_site
from tests.test_client_ip_source import _follow_site


def test_parse_listen_ports_from_tags_and_text():
    assert parse_listen_ports([80, "8080", 80]) == [80, 8080]
    assert parse_listen_ports("80, 8080，8443") == [80, 8080, 8443]


def test_parse_listen_ports_rejects_non_numeric():
    with pytest.raises(ValueError, match="必须是数字"):
        parse_listen_ports(["80a"])


def test_port_from_url_uses_explicit_and_scheme_defaults():
    assert port_from_url("http://127.0.0.1:9010") == 9010
    assert port_from_url("https://waf.example.com") == 443
    assert port_from_url("http://waf.example.com") == 80
    assert port_from_url("https://waf.example.com", implicit=False) is None
    assert port_from_url("") is None


def test_validate_rejects_overlap_and_reserved():
    with pytest.raises(ValueError, match="相同端口"):
        validate_custom_listen_ports(
            custom_listen_ports=True,
            listen_http=True,
            listen_https=True,
            http_ports=[8080],
            https_ports=[8080],
        )
    reserved = reserved_listen_port_messages(panel_port=9010, api_port=8001)
    with pytest.raises(ValueError, match="管理面板"):
        validate_custom_listen_ports(
            custom_listen_ports=True,
            listen_http=True,
            listen_https=False,
            http_ports=[9010],
            https_ports=[],
            reserved=reserved,
        )
    with pytest.raises(ValueError, match="系统内部接口"):
        validate_custom_listen_ports(
            custom_listen_ports=True,
            listen_http=True,
            listen_https=False,
            http_ports=[8001],
            https_ports=[],
            reserved=reserved,
        )
    validate_custom_listen_ports(
        custom_listen_ports=True,
        listen_http=True,
        listen_https=False,
        http_ports=[8000, 9000],
        https_ports=[],
        reserved=reserved,
    )


def _other_site(**kwargs: object) -> SimpleNamespace:
    values = dict(
        enabled=True,
        listen_http=True,
        listen_https=False,
        custom_listen_ports=False,
        listen_http_ports="80",
        listen_https_ports="443",
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


def test_cross_site_same_protocol_share_is_allowed():
    others = [
        _other_site(custom_listen_ports=True, listen_http_ports="80,9088"),
    ]
    validate_cross_site_listen_ports(
        custom_listen_ports=True,
        listen_http=True,
        listen_https=False,
        http_ports=[9088],
        https_ports=[],
        other_sites=others,
    )


def test_cross_site_http_https_same_port_is_rejected():
    others = [
        _other_site(custom_listen_ports=True, listen_http_ports="9088"),
    ]
    with pytest.raises(ValueError, match="端口 9088 已被另一站点的 HTTP 占用"):
        validate_cross_site_listen_ports(
            custom_listen_ports=True,
            listen_http=False,
            listen_https=True,
            http_ports=[],
            https_ports=[9088],
            other_sites=others,
        )
    others_https = [
        _other_site(
            listen_http=False,
            listen_https=True,
            custom_listen_ports=True,
            listen_https_ports="9088",
        )
    ]
    with pytest.raises(ValueError, match="端口 9088 已被另一站点的 HTTPS 占用"):
        validate_cross_site_listen_ports(
            custom_listen_ports=True,
            listen_http=True,
            listen_https=False,
            http_ports=[9088],
            https_ports=[],
            other_sites=others_https,
        )


def test_cross_site_skips_disabled_and_default_80_443_share():
    others = [
        _other_site(enabled=False, custom_listen_ports=True, listen_http_ports="9088"),
        _other_site(),
    ]
    validate_cross_site_listen_ports(
        custom_listen_ports=True,
        listen_http=False,
        listen_https=True,
        http_ports=[],
        https_ports=[9088],
        other_sites=others,
    )
    validate_cross_site_listen_ports(
        custom_listen_ports=False,
        listen_http=True,
        listen_https=False,
        http_ports=[80],
        https_ports=[443],
        other_sites=[_other_site()],
    )


def test_https_on_engine_default_http_port_is_rejected():
    with pytest.raises(ValueError, match="系统默认 HTTP"):
        validate_cross_site_listen_ports(
            custom_listen_ports=True,
            listen_http=False,
            listen_https=True,
            http_ports=[],
            https_ports=[80],
            other_sites=[],
        )


def test_ports_for_db_dumps_lists():
    payload = ports_for_db({"listen_http_ports": [80, 8080], "listen_https_ports": [443]})
    assert payload["listen_http_ports"] == "80,8080"
    assert payload["listen_https_ports"] == "443"
    assert dump_listen_ports([], default=[80]) == "80"


def test_site_create_accepts_custom_ports():
    site = SiteCreate(
        name="t",
        domains=["example.com"],
        origin_host="127.0.0.1",
        custom_listen_ports=True,
        listen_http_ports=[80, 8080],
        listen_https_ports=[443],
    )
    assert site.listen_http_ports == [80, 8080]


def test_site_create_allows_unreserved_internal_looking_ports():
    site = SiteCreate(
        name="t",
        domains=["example.com"],
        origin_host="127.0.0.1",
        custom_listen_ports=True,
        listen_http=True,
        listen_https=False,
        listen_http_ports=[8000, 9000],
    )
    assert site.listen_http_ports == [8000, 9000]


def test_render_site_custom_http_ports():
    conf = render_site(
        _follow_site(
            listen_https=False,
            certificate_id=None,
            certificate=None,
            custom_listen_ports=True,
            listen_http_ports="80,8080",
            listen_https_ports="443",
        )
    )
    assert "listen 80;" in conf
    assert "listen 8080;" in conf
    assert "listen 443" not in conf


def test_render_site_custom_https_and_force_redirect():
    conf = render_site(
        _follow_site(
            force_https=True,
            custom_listen_ports=True,
            listen_http_ports="80,8080",
            listen_https_ports="8443",
        )
    )
    assert "listen 80;" in conf
    assert "listen 8080;" in conf
    assert "listen 8443 ssl;" in conf
    assert "return 301 https://$host:8443$request_uri;" in conf
    assert "listen 443" not in conf
