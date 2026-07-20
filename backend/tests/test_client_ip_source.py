from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.constants.client_ip import CLIENT_IP_SOURCE_DEFAULT, CLIENT_IP_SOURCE_VALUES
from app.schemas.site import SiteCreate
from app.services.nginx_conf import _real_ip_block, render_site


def test_client_ip_source_values():
    assert CLIENT_IP_SOURCE_DEFAULT == "remote_addr"
    assert "cf_connecting_ip" in CLIENT_IP_SOURCE_VALUES
    assert "xff_first" in CLIENT_IP_SOURCE_VALUES


def test_site_create_rejects_invalid_client_ip_source():
    with pytest.raises(ValidationError):
        SiteCreate(
            name="t",
            domains=["example.com"],
            origin_host="127.0.0.1",
            client_ip_source="invalid",
        )


def test_real_ip_block_cf():
    site = SimpleNamespace(client_ip_source="cf_connecting_ip")
    block = _real_ip_block(site)
    assert "CF-Connecting-IP" in block
    assert "set_real_ip_from" in block


def test_real_ip_block_xff_first_empty():
    site = SimpleNamespace(client_ip_source="xff_first")
    assert _real_ip_block(site) == ""


def test_render_site_includes_real_ip_for_cdn():
    site = SimpleNamespace(
        id=1,
        domain="cdn.example.com",
        extra_domains=None,
        origin_host="127.0.0.1",
        origin_protocol="http",
        origin_http_port=80,
        origin_https_port=443,
        client_ip_source="cf_connecting_ip",
        listen_http=True,
        listen_https=False,
        certificate_id=None,
        certificate=None,
    )
    conf = render_site(site)
    assert "CF-Connecting-IP" in conf
    assert 'set $waf_site_id "1"' in conf
