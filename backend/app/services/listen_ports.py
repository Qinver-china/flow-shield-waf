"""Parse and resolve per-site HTTP/HTTPS listen ports for the engine."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterable
from urllib.parse import urlparse

DEFAULT_HTTP_PORTS = [80]
DEFAULT_HTTPS_PORTS = [443]
# engine.nginx.conf `listen 80 default_server` — 非 SSL，与站点 HTTPS 80 冲突。
ENGINE_PLAIN_HTTP_PORTS = frozenset({80})


def port_from_url(url: str | None, *, implicit: bool = True) -> int | None:
    """Return the TCP port of a URL.

    When ``implicit`` is true, scheme defaults 80/443 are used if the URL
    has no explicit port. Reserved-port checks should pass ``implicit=False``
    so default HTTP/HTTPS site listens are not treated as panel occupancy.
    """
    if not url or not str(url).strip():
        return None
    text = str(url).strip()
    if "://" not in text:
        text = f"http://{text}"
    parsed = urlparse(text)
    if parsed.port:
        return parsed.port
    if not implicit:
        return None
    if parsed.scheme == "https":
        return 443
    if parsed.scheme == "http":
        return 80
    return None


def reserved_listen_port_messages(
    *,
    panel_port: int | None,
    api_port: int | None,
) -> dict[int, str]:
    reserved: dict[int, str] = {}
    if api_port and int(api_port) > 0:
        reserved[int(api_port)] = f"端口 {int(api_port)} 为系统内部接口，请换一个"
    if panel_port and int(panel_port) not in reserved:
        reserved[int(panel_port)] = f"端口 {int(panel_port)} 为管理面板占用，请换一个"
    return reserved


def parse_listen_ports(value: Any) -> list[int]:
    """Normalize tags / comma-separated text / ints into unique ports."""
    raw_items: list[str] = []
    if value is None or value == "":
        return []
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        raw_items = [str(int(value))]
    elif isinstance(value, str):
        raw_items = value.replace("，", ",").split(",")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                raw_items.append(str(int(item)))
            elif isinstance(item, str):
                raw_items.extend(item.replace("，", ",").split(","))
    else:
        raise ValueError("监听端口格式无效")

    ports: list[int] = []
    seen: set[int] = set()
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        if not text.isdigit():
            raise ValueError(f"监听端口必须是数字：{item}")
        port = int(text)
        if port < 1 or port > 65535:
            raise ValueError(f"监听端口超出范围：{port}")
        if port in seen:
            continue
        seen.add(port)
        ports.append(port)
    return ports


def dump_listen_ports(ports: list[int] | None, *, default: list[int]) -> str:
    values = list(ports or [])
    return ",".join(str(port) for port in (values or default))


def load_listen_ports(raw: str | None, *, default: list[int]) -> list[int]:
    try:
        ports = parse_listen_ports(raw)
    except ValueError:
        return list(default)
    return ports or list(default)


def validate_custom_listen_ports(
    *,
    custom_listen_ports: bool,
    listen_http: bool,
    listen_https: bool,
    http_ports: list[int],
    https_ports: list[int],
    reserved: dict[int, str] | None = None,
) -> None:
    if not custom_listen_ports:
        return
    if listen_http and not http_ports:
        raise ValueError("开启自定义访问端口后，HTTP 监听至少需要一个端口")
    if listen_https and not https_ports:
        raise ValueError("开启自定义访问端口后，HTTPS 监听至少需要一个端口")
    used: list[int] = []
    if listen_http:
        used.extend(http_ports)
    if listen_https:
        used.extend(https_ports)
    overlap = set(http_ports if listen_http else []) & set(https_ports if listen_https else [])
    if overlap:
        label = "、".join(str(port) for port in sorted(overlap))
        raise ValueError(f"HTTP 与 HTTPS 不能使用相同端口：{label}")
    for port in used:
        if reserved and port in reserved:
            raise ValueError(reserved[port])


def planned_listen_ports(
    *,
    custom_listen_ports: bool,
    listen_http: bool,
    listen_https: bool,
    http_ports: list[int],
    https_ports: list[int],
) -> tuple[list[int], list[int]]:
    """Resolve the ports this save would actually bind, matching nginx render."""
    site = SimpleNamespace(
        listen_http=listen_http,
        listen_https=listen_https,
        custom_listen_ports=custom_listen_ports,
        listen_http_ports=http_ports,
        listen_https_ports=https_ports,
    )
    return resolve_http_listen_ports(site), resolve_https_listen_ports(site)


def collect_occupied_listen_ports(sites: Iterable[Any]) -> tuple[set[int], set[int]]:
    """HTTP/HTTPS listen sets already bound by enabled sites."""
    occupied_http: set[int] = set()
    occupied_https: set[int] = set()
    for site in sites:
        if not getattr(site, "enabled", True):
            continue
        occupied_http.update(resolve_http_listen_ports(site))
        occupied_https.update(resolve_https_listen_ports(site))
    return occupied_http, occupied_https


def validate_listen_port_occupancy(
    *,
    http_ports: list[int],
    https_ports: list[int],
    occupied_http: set[int],
    occupied_https: set[int],
) -> None:
    """Reject cross-site HTTP vs HTTPS on the same TCP port.

    Same port + same protocol is allowed (shared 80/443). Engine always
    binds plain HTTP 80 as default_server, so HTTPS 80 is never legal.
    """
    occupied_http = set(occupied_http)
    occupied_https = set(occupied_https)
    http_clash = sorted(set(http_ports) & occupied_https)
    https_clash = sorted(set(https_ports) & (occupied_http | ENGINE_PLAIN_HTTP_PORTS))
    parts: list[str] = []
    if http_clash:
        label = "、".join(str(port) for port in http_clash)
        parts.append(f"端口 {label} 已被另一站点的 HTTPS 占用")
    if https_clash:
        site_clash = [port for port in https_clash if port in occupied_http]
        engine_clash = [port for port in https_clash if port not in occupied_http]
        if site_clash:
            label = "、".join(str(port) for port in site_clash)
            parts.append(f"端口 {label} 已被另一站点的 HTTP 占用")
        if engine_clash:
            label = "、".join(str(port) for port in engine_clash)
            parts.append(f"端口 {label} 已被系统默认 HTTP 监听占用")
    if parts:
        raise ValueError("；".join(parts))


async def load_other_enabled_sites(
    db: Any,
    *,
    exclude_site_id: int | None = None,
) -> list[Any]:
    """Load enabled sites for a one-shot occupancy check on save."""
    from sqlalchemy import select

    from app.models.site import Site

    stmt = select(Site).where(Site.enabled.is_(True))
    if exclude_site_id is not None:
        stmt = stmt.where(Site.id != exclude_site_id)
    return list((await db.execute(stmt)).scalars().all())


def validate_cross_site_listen_ports(
    *,
    custom_listen_ports: bool,
    listen_http: bool,
    listen_https: bool,
    http_ports: list[int],
    https_ports: list[int],
    other_sites: Iterable[Any],
) -> None:
    """Check this save against other enabled sites' resolved listen lists."""
    planned_http, planned_https = planned_listen_ports(
        custom_listen_ports=custom_listen_ports,
        listen_http=listen_http,
        listen_https=listen_https,
        http_ports=http_ports,
        https_ports=https_ports,
    )
    occupied_http, occupied_https = collect_occupied_listen_ports(other_sites)
    validate_listen_port_occupancy(
        http_ports=planned_http,
        https_ports=planned_https,
        occupied_http=occupied_http,
        occupied_https=occupied_https,
    )


def resolve_http_listen_ports(site: Any) -> list[int]:
    if not getattr(site, "listen_http", False):
        return []
    if not getattr(site, "custom_listen_ports", False):
        return list(DEFAULT_HTTP_PORTS)
    return load_listen_ports(
        getattr(site, "listen_http_ports", None), default=DEFAULT_HTTP_PORTS
    )


def resolve_https_listen_ports(site: Any) -> list[int]:
    if not getattr(site, "listen_https", False):
        return []
    if not getattr(site, "custom_listen_ports", False):
        return list(DEFAULT_HTTPS_PORTS)
    return load_listen_ports(
        getattr(site, "listen_https_ports", None), default=DEFAULT_HTTPS_PORTS
    )


def https_redirect_url(https_ports: list[int]) -> str:
    if not https_ports or 443 in https_ports:
        return "https://$host$request_uri"
    return f"https://$host:{https_ports[0]}$request_uri"


def ports_for_db(payload: dict) -> dict:
    """Convert list[int] listen port fields to comma-separated storage."""
    out = dict(payload)
    if "listen_http_ports" in out and not isinstance(out["listen_http_ports"], str):
        out["listen_http_ports"] = dump_listen_ports(
            out["listen_http_ports"], default=DEFAULT_HTTP_PORTS
        )
    if "listen_https_ports" in out and not isinstance(out["listen_https_ports"], str):
        out["listen_https_ports"] = dump_listen_ports(
            out["listen_https_ports"], default=DEFAULT_HTTPS_PORTS
        )
    return out
