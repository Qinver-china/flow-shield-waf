"""Parse, normalize and persist multi-domain site bindings."""

from __future__ import annotations

import json
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Site

_DOMAIN_SPLIT_RE = re.compile(r"[\s,;，；]+")
# Regular FQDN, or a single-label nginx wildcard like *.example.com
_DOMAIN_RE = re.compile(
    r"^(?:\*\.)?(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
)


def validate_domain(value: str) -> str:
    domain = value.strip().lower().rstrip(".")
    if not domain:
        raise ValueError("域名不能为空")
    if "*" in domain:
        # Only allow nginx-style leftmost wildcard: *.example.com
        if not domain.startswith("*.") or domain.count("*") != 1:
            raise ValueError(f"通配符仅支持 *.example.com 格式：{value}")
        if domain == "*." or domain.count(".") < 2:
            raise ValueError(f"通配符域名格式无效：{value}")
    if not _DOMAIN_RE.match(domain):
        raise ValueError(f"域名格式无效：{value}")
    return domain


def normalize_domain_list(domains: list[str] | str) -> list[str]:
    raw_items: list[str]
    if isinstance(domains, str):
        raw_items = [part for part in _DOMAIN_SPLIT_RE.split(domains) if part]
    else:
        raw_items = []
        for item in domains:
            if isinstance(item, str):
                raw_items.extend(part for part in _DOMAIN_SPLIT_RE.split(item) if part)

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        domain = validate_domain(item)
        if domain in seen:
            continue
        seen.add(domain)
        normalized.append(domain)

    if not normalized:
        raise ValueError("至少输入一个域名")
    return normalized


def site_domain_list(site: Site) -> list[str]:
    domains = [site.domain]
    if site.extra_domains:
        try:
            extras = json.loads(site.extra_domains)
        except json.JSONDecodeError:
            extras = []
        if isinstance(extras, list):
            for item in extras:
                if isinstance(item, str) and item and item not in domains:
                    domains.append(item)
    return domains


def apply_domains_to_site(site: Site, domains: list[str] | str) -> list[str]:
    normalized = normalize_domain_list(domains)
    site.domain = normalized[0]
    extras = normalized[1:]
    site.extra_domains = json.dumps(extras, ensure_ascii=False) if extras else None
    return normalized


def format_domains_display(domains: list[str]) -> str:
    return ", ".join(domains)


async def ensure_domains_available(
    db: AsyncSession,
    domains: list[str],
    *,
    exclude_site_id: int | None = None,
) -> None:
    rows = (await db.execute(select(Site))).scalars().all()
    taken: dict[str, int] = {}
    for site in rows:
        if exclude_site_id is not None and site.id == exclude_site_id:
            continue
        for domain in site_domain_list(site):
            taken[domain] = site.id

    conflicts = [domain for domain in domains if domain in taken]
    if conflicts:
        label = "、".join(conflicts)
        raise ValueError(f"以下域名已被其他站点使用：{label}")
