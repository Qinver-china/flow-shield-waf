"""BaoTa panel HTTP client."""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.services.panels.mapping import should_skip_site_name
from app.services.panels.types import PanelError, PemPair, RawPanelCert, RawPanelSite

log = logging.getLogger("waf.panels.baota")

_DEFAULT_API_IPS = ("127.0.0.1", "172.17.0.1")


def _md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def baota_request_token(api_key: str, request_time: str, *, prehashed: bool) -> str:
    inner = api_key if prehashed else _md5(api_key)
    return _md5(request_time + inner)


def baota_panel_origin(panel_url: str) -> str:
    """BaoTa API is scheme+host+port only; the UI security entrance is not part of the API."""
    parsed = urlparse(panel_url or "")
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return (panel_url or "").rstrip("/")


def join_panel_url(base: str, path: str) -> str:
    """Join an API path onto the BaoTa origin, dropping any security-entrance suffix."""
    root = baota_panel_origin(base)
    raw = path or "/"
    if "?" in raw:
        path_only, _, query = raw.partition("?")
        return f"{root}/{path_only.lstrip('/')}?{query}"
    return f"{root}/{raw.lstrip('/')}"


def prepare_baota_api_json(
    existing: dict[str, Any] | None,
    *,
    plaintext_secret: str,
    allow_ips: list[str] | tuple[str, ...] = _DEFAULT_API_IPS,
) -> tuple[dict[str, Any], str, bool]:
    """Merge API whitelist and return (api.json, key stored in WAF, prehashed)."""
    data = dict(existing or {})
    token = str(data.get("token") or "").strip()
    opened = data.get("open") in {True, "true", "True", 1, "1"}
    limit = data.get("limit_addr") or []
    if isinstance(limit, str):
        current_ips = [part.strip() for part in limit.replace(",", " ").split() if part.strip()]
    elif isinstance(limit, list):
        current_ips = [str(item).strip() for item in limit if str(item).strip()]
    else:
        current_ips = []
    merged_ips = list(dict.fromkeys([*current_ips, *[str(ip).strip() for ip in allow_ips if str(ip).strip()]]))
    data["open"] = True
    data["limit_addr"] = merged_ips
    if opened and token:
        return data, token, True
    data["token"] = _md5(plaintext_secret)
    return data, plaintext_secret, False


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _pem_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if "BEGIN " in text and "PRIVATE KEY" in text:
        return text
    if "BEGIN CERTIFICATE" in text:
        return text
    return None


class BaotaAdapter:
    def __init__(
        self,
        *,
        panel_url: str,
        api_key: str,
        verify_tls: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.panel_url = baota_panel_origin(panel_url)
        self.api_key = api_key or ""
        self.verify_tls = verify_tls
        extra = extra or {}
        self.prehashed = bool(extra.get("baota_token_prehashed"))

    async def _post(self, path: str, fields: dict[str, Any] | None = None) -> Any:
        if not self.api_key.strip():
            raise PanelError("此面板未配置 API 密钥，请在系统设置中补全")
        request_time = str(int(time.time()))
        payload = {
            "request_time": request_time,
            "request_token": baota_request_token(
                self.api_key, request_time, prehashed=self.prehashed
            ),
        }
        if fields:
            payload.update(fields)
        url = join_panel_url(self.panel_url, path)
        try:
            async with httpx.AsyncClient(verify=self.verify_tls, timeout=20.0) as client:
                resp = await client.post(url, data=payload)
        except httpx.RequestError as exc:
            raise PanelError(f"无法连接宝塔面板：{exc}") from exc
        if resp.status_code >= 400:
            raise PanelError(f"宝塔面板返回 HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError as exc:
            snippet = (resp.text or "").strip()[:180]
            raise PanelError(f"宝塔面板返回非 JSON 响应：{snippet or '空内容'}") from exc
        if isinstance(data, dict) and data.get("status") is False:
            raise PanelError(str(data.get("msg") or "宝塔 API 调用失败"))
        return data

    async def test(self) -> str:
        await self._post("/data?action=getData", {"table": "sites", "type": "-1", "limit": "1"})
        return "已连接到宝塔面板"

    async def list_sites(self) -> list[RawPanelSite]:
        sites_raw = await self._post(
            "/data?action=getData",
            {"table": "sites", "type": "-1", "limit": "1000"},
        )
        domain_raw = await self._post(
            "/data?action=getData",
            {"table": "domain", "list": "true", "limit": "5000"},
        )
        site_rows = _extract_rows(sites_raw)
        domain_rows = _extract_rows(domain_raw)
        domains_by_pid: dict[int, list[dict[str, Any]]] = {}
        for row in domain_rows:
            pid = _as_int(row.get("pid") or row.get("id"))
            if pid is None:
                continue
            domains_by_pid.setdefault(pid, []).append(row)

        out: list[RawPanelSite] = []
        for row in site_rows:
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            skip = should_skip_site_name(name)
            site_id = _as_int(row.get("id"))
            bound = domains_by_pid.get(site_id or -1, [])
            domains: list[str] = []
            http_port: int | None = None
            https_port: int | None = None
            for item in bound:
                domain = str(item.get("name") or "").strip().lower().rstrip(".")
                if domain and domain not in domains:
                    domains.append(domain)
                port = _as_int(item.get("port"))
                if port == 443:
                    https_port = port
                elif port is not None:
                    http_port = http_port or port
            if not domains:
                domains = [name.lower().rstrip(".")]
            ssl_info = row.get("ssl") if isinstance(row.get("ssl"), dict) else {}
            has_ssl = bool(ssl_info) or _as_bool(row.get("ssl"))
            ssl_not_after = None
            if ssl_info:
                ssl_not_after = str(ssl_info.get("notAfter") or ssl_info.get("endtime") or "") or None
                has_ssl = True
            out.append(
                RawPanelSite(
                    key=name,
                    name=name,
                    domains=domains,
                    http_port=http_port,
                    https_port=https_port,
                    has_ssl=has_ssl,
                    ssl_not_after=ssl_not_after,
                    skip_reason=skip,
                )
            )
        return out

    async def list_certificates(self) -> list[RawPanelCert]:
        data = await self._post("/ssl?action=GetCertList")
        rows = data if isinstance(data, list) else _extract_rows(data)
        out: list[RawPanelCert] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            dns = row.get("dns") or []
            if isinstance(dns, str):
                domains = [dns]
            elif isinstance(dns, list):
                domains = [str(item).strip() for item in dns if str(item).strip()]
            else:
                domains = []
            subject = str(row.get("subject") or (domains[0] if domains else "")).strip()
            if not subject:
                continue
            out.append(
                RawPanelCert(
                    key=subject,
                    name=subject,
                    domains=domains or [subject],
                    not_after=str(row.get("notAfter") or "") or None,
                )
            )
        return out

    async def fetch_site_cert(self, site_key: str) -> PemPair | None:
        data = await self._post("/site?action=GetSSL", {"siteName": site_key})
        if not isinstance(data, dict):
            return None
        cert_pem = _pem_text(data.get("csr"))
        key_pem = _pem_text(data.get("key"))
        if not cert_pem or not key_pem:
            return None
        force_https = _as_bool(data.get("httpTohttps"))
        pair = PemPair(cert_pem=cert_pem, key_pem=key_pem, name=site_key)
        pair_force = force_https  # attached via extra attr for importer
        setattr(pair, "force_https", pair_force)
        cert_data = data.get("cert_data") if isinstance(data.get("cert_data"), dict) else {}
        setattr(pair, "ssl_not_after", str((cert_data or {}).get("notAfter") or "") or None)
        return pair

    async def fetch_cert(self, cert_key: str) -> PemPair:
        pair = await self.fetch_site_cert(cert_key)
        if pair is None:
            raise PanelError(f"未能从宝塔读取证书：{cert_key}")
        return pair

    async def push_site_cert(self, site_key: str, cert_pem: str, key_pem: str) -> None:
        """Deploy a PEM pair onto a BaoTa website via SetSSL.

        BaoTa 11.x turns on HTTP→HTTPS redirect after SetSSL; that is a
        separate ``HttpToHttps`` feature and is closed here with ``CloseToHttps``.

        Args:
            site_key: BaoTa site name (``RawPanelSite.key``).
            cert_pem: Certificate chain in PEM format.
            key_pem: Matching private key in PEM format.

        Raises:
            PanelError: If the BaoTa API rejects the certificate.
        """
        await self._post(
            "/site?action=SetSSL",
            {"siteName": site_key, "key": key_pem, "csr": cert_pem},
        )
        try:
            await self._post("/site?action=CloseToHttps", {"siteName": site_key})
        except PanelError as exc:
            log.warning("baota CloseToHttps failed site=%s: %s", site_key, exc)


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            inner = data.get("data") or data.get("list") or data.get("items")
            if isinstance(inner, list):
                return [item for item in inner if isinstance(item, dict)]
    return []


def _as_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
