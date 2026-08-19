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


def test_site_create_rejects_force_https_without_listen_https():
    with pytest.raises(ValidationError):
        SiteCreate(
            name="t",
            domains=["example.com"],
            origin_host="127.0.0.1",
            listen_http=True,
            listen_https=False,
            force_https=True,
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
        force_https=False,
        certificate_id=None,
        certificate=None,
    )
    conf = render_site(site)
    assert "CF-Connecting-IP" in conf
    assert 'set $waf_site_id "1"' in conf


def test_render_site_force_https_redirect():
    cert = SimpleNamespace(
        cert_path="/etc/nginx/certs/example.crt",
        key_path="/etc/nginx/certs/example.key",
    )
    site = SimpleNamespace(
        id=2,
        domain="example.com",
        extra_domains=None,
        origin_host="127.0.0.1",
        origin_protocol="http",
        origin_http_port=80,
        origin_https_port=443,
        client_ip_source="remote_addr",
        listen_http=True,
        listen_https=True,
        force_https=True,
        certificate_id=1,
        certificate=cert,
    )
    conf = render_site(site)
    assert "return 301 https://$host$request_uri;" in conf
    assert "location ^~ /.well-known/acme-challenge/" in conf
    assert "alias /data/acme/http-01/;" in conf
    assert "location / {\n        return 301 https://$host$request_uri;" in conf
    assert "listen 80;" in conf
    assert "listen 443 ssl;" in conf
    assert conf.count("listen 80;") == 1
    assert "/etc/nginx/certs/example.crt" in conf


def test_render_site_disable_content_buffering():
    site = SimpleNamespace(
        id=3,
        domain="local.example.com",
        extra_domains=None,
        origin_host="127.0.0.1",
        origin_protocol="http",
        origin_http_port=80,
        origin_https_port=443,
        client_ip_source="remote_addr",
        listen_http=True,
        listen_https=False,
        force_https=False,
        disable_content_buffering=True,
        certificate_id=None,
        certificate=None,
    )
    conf = render_site(site)
    assert "proxy_buffering off;" in conf
    assert "location ^~ /.well-known/acme-challenge/" in conf


def test_render_site_keeps_default_buffering():
    site = SimpleNamespace(
        id=4,
        domain="remote.example.com",
        extra_domains=None,
        origin_host="10.0.0.2",
        origin_protocol="http",
        origin_http_port=80,
        origin_https_port=443,
        client_ip_source="remote_addr",
        listen_http=True,
        listen_https=False,
        force_https=False,
        disable_content_buffering=False,
        certificate_id=None,
        certificate=None,
    )
    conf = render_site(site)
    assert "proxy_buffering" not in conf
    assert "proxy_set_header X-Real-IP $waf_geoip_client;" in conf
    assert "proxy_set_header X-Forwarded-For $waf_geoip_client;" in conf
    assert 'proxy_set_header Connection $waf_connection_upgrade;' in conf
    assert "proxy_set_header X-WAF-Request-Id $waf_request_id;" in conf
    assert 'proxy_set_header Connection "upgrade";' not in conf


def _follow_site(**kwargs):
    cert = SimpleNamespace(
        cert_path="/etc/nginx/certs/example.crt",
        key_path="/etc/nginx/certs/example.key",
    )
    base = dict(
        id=10,
        domain="example.com",
        extra_domains=None,
        origin_host="host.docker.internal",
        origin_protocol="follow",
        origin_http_port=8080,
        origin_https_port=4343,
        client_ip_source="remote_addr",
        listen_http=True,
        listen_https=True,
        force_https=False,
        disable_content_buffering=False,
        certificate_id=1,
        certificate=cert,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_render_site_follow_splits_http_and_https_upstreams():
    conf = render_site(_follow_site())
    assert "map $scheme" not in conf
    assert "proxy_pass $waf_upstream_" not in conf
    assert "listen 80;" in conf
    assert "listen 443 ssl;" in conf
    assert "proxy_pass http://host.docker.internal:8080;" in conf
    assert "proxy_pass https://host.docker.internal:4343;" in conf
    http_block, https_block = conf.split("listen 443 ssl;", 1)
    assert "proxy_pass http://host.docker.internal:8080;" in http_block
    assert "proxy_pass https://" not in http_block
    assert "proxy_pass https://host.docker.internal:4343;" in https_block
    assert "proxy_pass http://" not in https_block


def test_render_site_follow_http_only_uses_http_origin():
    conf = render_site(_follow_site(listen_https=False, certificate_id=None, certificate=None))
    assert "listen 80;" in conf
    assert "listen 443" not in conf
    assert "proxy_pass http://host.docker.internal:8080;" in conf
    assert "proxy_pass https://" not in conf


def test_render_site_follow_force_https_uses_https_origin():
    conf = render_site(_follow_site(force_https=True))
    assert "return 301 https://$host$request_uri;" in conf
    assert conf.count("listen 80;") == 1
    assert "proxy_pass https://host.docker.internal:4343;" in conf
    assert "proxy_pass http://" not in conf
