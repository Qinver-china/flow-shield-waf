"""Panel adapters, origin mapping, and local bootstrap CLI."""
from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cli.bootstrap_local_panel import upsert_local_panel
from app.models.panel_connection import PanelConnection
from app.services.panels.baota import (
    BaotaAdapter,
    baota_panel_origin,
    baota_request_token,
    join_panel_url,
    prepare_baota_api_json,
)
from app.services.panels.mapping import default_origin_host, remap_listen_ports, should_skip_site_name
from app.services.panels.onepanel import OnePanelAdapter, onepanel_token_hmac, onepanel_token_md5


class FakeResponse:
    def __init__(self, payload, status=200, text=""):
        self._payload = payload
        self.status_code = status
        self.text = text or ""

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class FakeAsyncClient:
    def __init__(self, handler):
        self.handler = handler

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def post(self, url, data=None):
        return self.handler("POST", url, data=data)

    async def request(self, method, url, headers=None, json=None):
        return self.handler(method, url, headers=headers, json=json)


def test_remap_listen_ports_same_server():
    assert remap_listen_ports(80, 443, same_server=True) == (8080, 4343)
    assert remap_listen_ports(8080, 8443, same_server=True) == (8080, 8443)
    assert remap_listen_ports(80, 443, same_server=False) == (80, 443)


def test_default_origin_host():
    assert default_origin_host("https://panel.example.com:8888/x", same_server=True) == "host.docker.internal"
    assert default_origin_host("https://panel.example.com:8888/x", same_server=False) == "panel.example.com"


def test_should_skip_site_name():
    assert should_skip_site_name("phpmyadmin")
    assert should_skip_site_name("0.default")
    assert should_skip_site_name("blog") is None


def test_baota_request_token_prehashed():
    secret = "plain-secret"
    hashed = hashlib.md5(secret.encode()).hexdigest()
    ts = "1700000000"
    assert baota_request_token(secret, ts, prehashed=False) == hashlib.md5(
        (ts + hashed).encode()
    ).hexdigest()
    assert baota_request_token(hashed, ts, prehashed=True) == hashlib.md5(
        (ts + hashed).encode()
    ).hexdigest()
    assert baota_request_token(hashed, ts, prehashed=False) != baota_request_token(
        hashed, ts, prehashed=True
    )


def test_join_panel_url_drops_entrance():
    assert baota_panel_origin("https://host.docker.internal:8888/safe") == "https://host.docker.internal:8888"
    assert (
        join_panel_url("https://host.docker.internal:8888/safe", "/data?action=getData")
        == "https://host.docker.internal:8888/data?action=getData"
    )
    assert (
        join_panel_url("https://host.docker.internal:8888", "/data?action=getData")
        == "https://host.docker.internal:8888/data?action=getData"
    )


def test_prepare_baota_api_json_opens_and_merges_whitelist():
    data, stored, prehashed = prepare_baota_api_json(
        {"open": False, "limit_addr": ["10.0.0.1"]},
        plaintext_secret="abc",
    )
    assert prehashed is False
    assert stored == "abc"
    assert data["open"] is True
    assert data["token"] == hashlib.md5(b"abc").hexdigest()
    assert data["limit_addr"] == ["10.0.0.1", "127.0.0.1", "172.17.0.1"]


def test_prepare_baota_api_json_keeps_existing_token():
    existing = {"open": True, "token": "already-md5", "limit_addr": ["127.0.0.1"]}
    data, stored, prehashed = prepare_baota_api_json(existing, plaintext_secret="unused")
    assert prehashed is True
    assert stored == "already-md5"
    assert data["token"] == "already-md5"
    assert "172.17.0.1" in data["limit_addr"]


def test_onepanel_tokens_are_stable():
    hmac_token = onepanel_token_hmac("key", "111")
    md5_token = onepanel_token_md5("key", "111")
    assert len(hmac_token) == 64
    assert len(md5_token) == 32
    assert hmac_token != md5_token


@pytest.mark.asyncio
async def test_baota_list_sites_http_mock():
    responses = [
        FakeResponse({"data": [{"id": 1, "name": "blog.example.com", "ssl": {}}]}),
        FakeResponse(
            {
                "data": [
                    {"pid": 1, "name": "blog.example.com", "port": 80},
                    {"pid": 1, "name": "www.example.com", "port": 443},
                ]
            }
        ),
    ]

    def handler(method, url, **_kwargs):
        assert url.startswith("https://host.docker.internal:8888/data")
        assert "/safe/" not in url
        return responses.pop(0)

    adapter = BaotaAdapter(
        panel_url="https://host.docker.internal:8888/safe",
        api_key="secret",
        extra={"baota_token_prehashed": True},
    )
    assert adapter.panel_url == "https://host.docker.internal:8888"
    with patch("app.services.panels.baota.httpx.AsyncClient", return_value=FakeAsyncClient(handler)):
        sites = await adapter.list_sites()
    assert len(sites) == 1
    assert sites[0].domains == ["blog.example.com", "www.example.com"]
    assert sites[0].http_port == 80
    assert sites[0].https_port == 443
    assert sites[0].has_ssl is False


def _assert_onepanel_search_order(body: dict) -> None:
    """1Panel WebsiteSearch/SSLSearch require orderBy + order (gin required/oneof)."""
    assert body.get("orderBy") == "created_at"
    assert body.get("order") == "null"


@pytest.mark.asyncio
async def test_onepanel_list_sites_http_mock():
    def handler(method, url, **kwargs):
        assert method == "POST"
        assert url == "http://host.docker.internal:10086/api/v2/websites/search"
        assert "1Panel-Token" in (kwargs.get("headers") or {})
        _assert_onepanel_search_order(kwargs.get("json") or {})
        return FakeResponse(
            {
                "code": 200,
                "data": {
                    "items": [
                        {
                            "id": 9,
                            "alias": "shop",
                            "primaryDomain": "shop.example.com",
                            "protocol": "HTTP",
                            "httpPort": 80,
                            "domains": [{"domain": "www.shop.example.com", "port": 80}],
                        }
                    ]
                },
            }
        )

    adapter = OnePanelAdapter(
        panel_url="http://host.docker.internal:10086/entrance",
        api_key="panel-key",
    )
    with patch("app.services.panels.onepanel.httpx.AsyncClient", return_value=FakeAsyncClient(handler)):
        sites = await adapter.list_sites()
    assert adapter.panel_url == "http://host.docker.internal:10086"
    assert sites[0].key == "9"
    assert "shop.example.com" in sites[0].domains


@pytest.mark.asyncio
async def test_onepanel_test_sends_required_search_order():
    captured = {}

    def handler(method, url, **kwargs):
        captured["json"] = kwargs.get("json")
        return FakeResponse({"code": 200, "data": {"items": []}})

    adapter = OnePanelAdapter(panel_url="http://panel.example:10086", api_key="panel-key")
    with patch("app.services.panels.onepanel.httpx.AsyncClient", return_value=FakeAsyncClient(handler)):
        message = await adapter.test()
    assert message == "已连接到 1Panel"
    _assert_onepanel_search_order(captured["json"] or {})


@pytest.mark.asyncio
async def test_onepanel_list_certificates_sends_search_order():
    captured = {}

    def handler(method, url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse({"code": 200, "data": {"items": []}})

    adapter = OnePanelAdapter(panel_url="http://panel.example:10086", api_key="panel-key")
    with patch("app.services.panels.onepanel.httpx.AsyncClient", return_value=FakeAsyncClient(handler)):
        certs = await adapter.list_certificates()
    assert certs == []
    assert captured["url"].endswith("/api/v2/websites/ssl/search")
    _assert_onepanel_search_order(captured["json"] or {})


@pytest.mark.asyncio
async def test_bootstrap_skips_existing_same_server_account():
    existing = PanelConnection(
        name="本机宝塔",
        provider="baota",
        panel_url="http://host.docker.internal:8888",
        same_server=True,
    )
    existing.id = 3
    result = MagicMock()
    result.scalars.return_value.first.return_value = existing
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=db)
    session.__aexit__ = AsyncMock(return_value=False)
    with patch("app.cli.bootstrap_local_panel.SessionLocal", return_value=session):
        status, row = await upsert_local_panel(
            provider="baota",
            name="本机宝塔",
            panel_url="http://host.docker.internal:8888/new",
            api_key="changed",
        )
    assert status == "skipped"
    assert row is existing
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_baota_push_site_cert_calls_set_ssl():
    captured = []

    def handler(method, url, **kwargs):
        captured.append({"url": url, "data": kwargs.get("data")})
        return FakeResponse({"status": True, "msg": "证书已保存!"})

    adapter = BaotaAdapter(panel_url="http://127.0.0.1:8888", api_key="secret")
    with patch("app.services.panels.baota.httpx.AsyncClient", return_value=FakeAsyncClient(handler)):
        await adapter.push_site_cert("blog.example.com", "CERT", "KEY")
    assert captured[0]["url"].endswith("/site?action=SetSSL")
    assert captured[0]["data"]["siteName"] == "blog.example.com"
    assert captured[0]["data"]["csr"] == "CERT"
    assert captured[0]["data"]["key"] == "KEY"
    assert captured[1]["url"].endswith("/site?action=CloseToHttps")
    assert captured[1]["data"]["siteName"] == "blog.example.com"


@pytest.mark.asyncio
async def test_baota_push_succeeds_when_close_https_fails():
    def handler(method, url, **kwargs):
        if "CloseToHttps" in url:
            return FakeResponse({"status": False, "msg": "设置失败"})
        return FakeResponse({"status": True, "msg": "证书已保存!"})

    adapter = BaotaAdapter(panel_url="http://127.0.0.1:8888", api_key="secret")
    with patch("app.services.panels.baota.httpx.AsyncClient", return_value=FakeAsyncClient(handler)):
        await adapter.push_site_cert("blog.example.com", "CERT", "KEY")


@pytest.mark.asyncio
async def test_onepanel_push_site_cert_imports_https():
    captured = []

    def handler(method, url, **kwargs):
        captured.append({"method": method, "url": url, "json": kwargs.get("json")})
        if method == "GET":
            return FakeResponse({"code": 200, "data": {"httpConfig": "HTTPToHTTPS", "hsts": True}})
        return FakeResponse({"code": 200, "data": {}})

    adapter = OnePanelAdapter(panel_url="http://panel.example:10086", api_key="panel-key")
    with patch("app.services.panels.onepanel.httpx.AsyncClient", return_value=FakeAsyncClient(handler)):
        await adapter.push_site_cert("9", "CERT", "KEY")
    assert captured[0]["method"] == "GET"
    assert captured[0]["url"].endswith("/api/v2/websites/9/https")
    assert captured[1]["method"] == "POST"
    body = captured[1]["json"]
    assert body["type"] == "import"
    assert body["importType"] == "paste"
    assert body["certificate"] == "CERT"
    assert body["privateKey"] == "KEY"
    assert body["httpConfig"] == "HTTPAlso"
    assert body["hsts"] is True


@pytest.mark.asyncio
async def test_onepanel_push_keeps_https_only():
    captured = []

    def handler(method, url, **kwargs):
        captured.append(kwargs.get("json"))
        if method == "GET":
            return FakeResponse({"code": 200, "data": {"httpConfig": "HTTPSOnly"}})
        return FakeResponse({"code": 200, "data": {}})

    adapter = OnePanelAdapter(panel_url="http://panel.example:10086", api_key="panel-key")
    with patch("app.services.panels.onepanel.httpx.AsyncClient", return_value=FakeAsyncClient(handler)):
        await adapter.push_site_cert("9", "CERT", "KEY")
    assert captured[1]["httpConfig"] == "HTTPSOnly"
