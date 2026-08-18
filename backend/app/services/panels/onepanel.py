"""1Panel HTTP client."""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.services.panels.mapping import should_skip_site_name
from app.services.panels.types import PanelError, PemPair, RawPanelCert, RawPanelSite


def onepanel_token_hmac(api_key: str, timestamp: str) -> str:
    return hmac.new(
        api_key.encode("utf-8"),
        f"1panel:{timestamp}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def onepanel_token_md5(api_key: str, timestamp: str) -> str:
    return hashlib.md5(f"1panel{api_key}{timestamp}".encode("utf-8")).hexdigest()


def _pem_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if "BEGIN " in text:
        return text
    return None


class OnePanelAdapter:
    def __init__(
        self,
        *,
        panel_url: str,
        api_key: str,
        verify_tls: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> None:
        parsed = urlparse(panel_url)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else panel_url.rstrip("/")
        self.panel_url = origin.rstrip("/")
        self.api_key = api_key or ""
        self.verify_tls = verify_tls
        extra = extra or {}
        self._auth_mode = str(extra.get("onepanel_auth") or "hmac")

    def _headers(self, *, md5: bool = False) -> dict[str, str]:
        ts = str(int(time.time()))
        token = onepanel_token_md5(self.api_key, ts) if md5 else onepanel_token_hmac(self.api_key, ts)
        return {"1Panel-Timestamp": ts, "1Panel-Token": token}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        allow_md5_fallback: bool = True,
    ) -> Any:
        if not self.api_key.strip():
            raise PanelError("此面板未配置 API 密钥，请在系统设置中补全")
        url = urljoin(self.panel_url + "/", path.lstrip("/"))
        use_md5 = self._auth_mode == "md5"
        try:
            data, status, message = await self._send(method, url, json_body, md5=use_md5)
        except httpx.RequestError as exc:
            raise PanelError(f"无法连接 1Panel：{exc}") from exc
        if status == 401 and allow_md5_fallback and not use_md5:
            try:
                data, status, message = await self._send(method, url, json_body, md5=True)
            except httpx.RequestError as exc:
                raise PanelError(f"无法连接 1Panel：{exc}") from exc
            if status < 400:
                self._auth_mode = "md5"
        if status >= 400:
            raise PanelError(message or f"1Panel 返回 HTTP {status}")
        if isinstance(data, dict):
            code = data.get("code")
            if isinstance(code, int) and code not in {0, 200}:
                raise PanelError(str(data.get("message") or "1Panel API 调用失败"))
            if "data" in data:
                return data.get("data")
        return data

    async def _send(
        self, method: str, url: str, json_body: Any, *, md5: bool
    ) -> tuple[Any, int, str]:
        async with httpx.AsyncClient(verify=self.verify_tls, timeout=20.0) as client:
            resp = await client.request(
                method,
                url,
                headers=self._headers(md5=md5),
                json=json_body,
            )
        message = ""
        try:
            payload = resp.json()
            if isinstance(payload, dict):
                message = str(payload.get("message") or "")
        except ValueError:
            payload = None
            message = (resp.text or "").strip()[:180]
        if resp.status_code >= 400 and not message:
            message = f"1Panel 返回 HTTP {resp.status_code}"
        return payload, resp.status_code, message

    async def test(self) -> str:
        await self._request(
            "POST",
            "/api/v2/websites/search",
            json_body=_page_search(page=1, page_size=1),
        )
        return "已连接到 1Panel"

    async def list_sites(self) -> list[RawPanelSite]:
        data = await self._request(
            "POST",
            "/api/v2/websites/search",
            json_body=_page_search(page=1, page_size=1000, name=""),
        )
        rows = _items(data)
        out: list[RawPanelSite] = []
        for row in rows:
            name = str(row.get("alias") or row.get("primaryDomain") or row.get("primary_domain") or "").strip()
            if not name:
                continue
            skip = should_skip_site_name(name)
            domains = _site_domains(row)
            if not domains:
                domains = [name]
            ssl_id = row.get("websiteSSLID") or row.get("websiteSSLId") or row.get("website_ssl_id")
            protocol = str(row.get("protocol") or "").upper()
            has_ssl = bool(ssl_id) or protocol == "HTTPS"
            http_port = _as_int(row.get("httpPort") or row.get("http_port"))
            https_port = _as_int(row.get("httpsPort") or row.get("https_port"))
            for item in row.get("domains") or []:
                if not isinstance(item, dict):
                    continue
                port = _as_int(item.get("port"))
                if port == 443:
                    https_port = https_port or port
                elif port is not None:
                    http_port = http_port or port
            out.append(
                RawPanelSite(
                    key=str(row.get("id") or name),
                    name=name,
                    domains=domains,
                    http_port=http_port,
                    https_port=https_port,
                    has_ssl=has_ssl,
                    ssl_not_after=_ssl_not_after(row),
                    skip_reason=skip,
                )
            )
        return out

    async def list_certificates(self) -> list[RawPanelCert]:
        data = await self._request(
            "POST",
            "/api/v2/websites/ssl/search",
            json_body=_page_search(page=1, page_size=1000),
        )
        rows = _items(data)
        out: list[RawPanelCert] = []
        for row in rows:
            cert_id = row.get("id")
            name = str(row.get("primaryDomain") or row.get("primary_domain") or row.get("description") or "").strip()
            if cert_id is None or not name:
                continue
            domains = _cert_domains(row)
            out.append(
                RawPanelCert(
                    key=str(cert_id),
                    name=name,
                    domains=domains or [name],
                    not_after=str(row.get("expireDate") or row.get("expire_date") or "") or None,
                )
            )
        return out

    async def fetch_site_cert(self, site_key: str) -> PemPair | None:
        try:
            site_id = int(site_key)
        except (TypeError, ValueError):
            return None
        try:
            data = await self._request("GET", f"/api/v2/websites/ssl/website/{site_id}")
        except PanelError:
            https = await self._request("GET", f"/api/v2/websites/{site_id}/https")
            ssl = https.get("SSL") if isinstance(https, dict) else None
            if not isinstance(ssl, dict):
                ssl = https if isinstance(https, dict) else {}
            ssl_id = ssl.get("id") or (https.get("websiteSSLId") if isinstance(https, dict) else None)
            if not ssl_id:
                return None
            data = await self._request("GET", f"/api/v2/websites/ssl/{ssl_id}")
        return _pem_from_ssl(data, fallback_name=site_key)

    async def fetch_cert(self, cert_key: str) -> PemPair:
        data = await self._request("GET", f"/api/v2/websites/ssl/{cert_key}")
        pair = _pem_from_ssl(data, fallback_name=str(cert_key))
        if pair is None:
            raise PanelError(f"未能从 1Panel 读取证书：{cert_key}")
        return pair

    async def push_site_cert(self, site_key: str, cert_pem: str, key_pem: str) -> None:
        """Deploy a PEM pair onto a 1Panel website HTTPS config.

        Force HTTP→HTTPS (``HTTPToHTTPS``) is not enabled: 1Panel GET defaults
        that value when unset, and the origin behind WAF should keep HTTP.

        Args:
            site_key: 1Panel website id as a string.
            cert_pem: Certificate chain in PEM format.
            key_pem: Matching private key in PEM format.

        Raises:
            PanelError: If the website id is invalid or the API rejects the cert.
        """
        try:
            site_id = int(site_key)
        except (TypeError, ValueError) as exc:
            raise PanelError(f"无效的 1Panel 站点：{site_key}") from exc
        https: dict[str, Any] = {}
        try:
            payload = await self._request("GET", f"/api/v2/websites/{site_id}/https")
            if isinstance(payload, dict):
                https = payload
        except PanelError:
            https = {}
        http_config = str(https.get("httpConfig") or https.get("HttpConfig") or "").strip()
        if http_config != "HTTPSOnly":
            http_config = "HTTPAlso"
        ssl_protocol = https.get("SSLProtocol") or https.get("sslProtocol")
        if not isinstance(ssl_protocol, list) or not ssl_protocol:
            ssl_protocol = ["TLSv1.2", "TLSv1.3"]
        algorithm = str(https.get("algorithm") or https.get("Algorithm") or "")
        hsts = bool(https.get("hsts") or https.get("HSTS") or False)
        http3 = bool(https.get("http3") or https.get("Http3") or False)
        await self._request(
            "POST",
            f"/api/v2/websites/{site_id}/https",
            json_body={
                "websiteId": site_id,
                "enable": True,
                "type": "import",
                "importType": "paste",
                "privateKey": key_pem,
                "certificate": cert_pem,
                "httpConfig": http_config,
                "SSLProtocol": ssl_protocol,
                "algorithm": algorithm,
                "hsts": hsts,
                "http3": http3,
            },
        )


def _page_search(page: int, page_size: int, **extra: Any) -> dict[str, Any]:
    """Build a 1Panel list-search body.

    WebsiteSearch requires orderBy/order (gin ``required`` + ``oneof``). SSL search
    made them optional later, but older panels still reject a missing pair.
    """
    return {
        "page": page,
        "pageSize": page_size,
        "orderBy": "created_at",
        "order": "null",
        **extra,
    }


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "list"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return [item for item in inner if isinstance(item, dict)]
    return []


def _site_domains(row: dict[str, Any]) -> list[str]:
    out: list[str] = []
    primary = str(row.get("primaryDomain") or row.get("primary_domain") or "").strip().lower().rstrip(".")
    if primary:
        out.append(primary)
    domains = row.get("domains")
    if isinstance(domains, list):
        for item in domains:
            if isinstance(item, str):
                name = item.strip().lower().rstrip(".")
            elif isinstance(item, dict):
                name = str(item.get("domain") or item.get("name") or "").strip().lower().rstrip(".")
            else:
                name = ""
            if name and name not in out:
                out.append(name)
    return out


def _cert_domains(row: dict[str, Any]) -> list[str]:
    domains = row.get("domains") or row.get("dns") or []
    if isinstance(domains, str):
        return [part.strip() for part in domains.replace(",", "\n").split() if part.strip()]
    if isinstance(domains, list):
        out: list[str] = []
        for item in domains:
            name = str(item).strip()
            if name and name not in out:
                out.append(name)
        return out
    return []


def _ssl_not_after(row: dict[str, Any]) -> str | None:
    ssl = row.get("ssl") or row.get("SSL") or {}
    if isinstance(ssl, dict):
        value = ssl.get("expireDate") or ssl.get("expire_date") or ssl.get("notAfter")
        if value:
            return str(value)
    return None


def _pem_from_ssl(data: Any, *, fallback_name: str) -> PemPair | None:
    if not isinstance(data, dict):
        return None
    cert_pem = _pem_text(data.get("pem") or data.get("certificate") or data.get("csr"))
    key_pem = _pem_text(data.get("privateKey") or data.get("private_key") or data.get("key"))
    if not cert_pem or not key_pem:
        return None
    name = str(data.get("primaryDomain") or data.get("primary_domain") or fallback_name)
    pair = PemPair(cert_pem=cert_pem, key_pem=key_pem, name=name)
    https = data.get("httpTohttps") or data.get("http_to_https") or data.get("HTTPS")
    setattr(pair, "force_https", bool(https) if not isinstance(https, dict) else False)
    return pair


def _as_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
