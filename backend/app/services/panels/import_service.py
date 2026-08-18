"""Import sites / certificates from a saved panel connection."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Certificate, PanelConnection, Site
from app.schemas.panel_connection import (
    PanelCertPreview,
    PanelImportItemResult,
    PanelImportResult,
    PanelSitePreview,
)
from app.services import certificate_store, nginx_conf, rule_sync
from app.services.certificate_ops import (
    apply_pem_to_certificate,
    fingerprint_map,
    leaf_sha256,
    persist_new_certificate,
    reload_sites_using_certificate,
)
from app.services.origin import validate_origin_host
from app.services.panels import get_adapter
from app.services.panels.mapping import default_origin_host, remap_listen_ports
from app.services.panels.types import PanelError, PemPair, RawPanelSite
from app.services.site_domains import (
    apply_domains_to_site,
    ensure_domains_available,
    normalize_domain_list,
    site_domain_list,
)

log = logging.getLogger("waf.panels.import")


def adapter_for(row: PanelConnection):
    return get_adapter(
        provider=row.provider,
        panel_url=row.panel_url,
        api_key=row.api_key or "",
        verify_tls=bool(row.verify_tls),
        extra=row.extra or {},
    )


def _occupied_domains(sites: list[Site]) -> dict[str, int]:
    taken: dict[str, int] = {}
    for site in sites:
        for domain in site_domain_list(site):
            taken[domain] = site.id
    return taken


def _normalize_domain_set(domains: list[str]) -> set[str]:
    return {item.strip().lower().rstrip(".") for item in domains if item and item.strip()}


def _domains_set(value: str | list[str] | None) -> set[str]:
    """Normalize stored or panel domain lists into a comparable set.

    Args:
        value: Comma/space separated text, or a list of domain names.

    Returns:
        Lowercased domains with trailing dots stripped.
    """
    if value is None:
        return set()
    parts = value.replace(",", " ").split() if isinstance(value, str) else value
    return _normalize_domain_set(parts)


async def preview_sites(
    db: AsyncSession, row: PanelConnection, *, purpose: str | None = None
) -> list[PanelSitePreview]:
    adapter = adapter_for(row)
    raw_sites = await adapter.list_sites()
    for_sync = (purpose or "").strip().lower() == "sync"
    taken = {} if for_sync else _occupied_domains((await db.execute(select(Site))).scalars().all())
    items: list[PanelSitePreview] = []
    for site in raw_sites:
        http_port, https_port = remap_listen_ports(
            site.http_port, site.https_port, same_server=bool(row.same_server)
        )
        skip = site.skip_reason
        already = False
        if not skip:
            try:
                domains = normalize_domain_list(site.domains)
            except ValueError as exc:
                skip = str(exc)
                domains = site.domains
            else:
                site.domains = domains
                if not for_sync:
                    conflicts = [d for d in domains if d in taken]
                    if conflicts:
                        already = True
                        skip = f"域名已存在：{'、'.join(conflicts)}"
                    elif not domains:
                        skip = "没有可导入的域名"
                elif not domains:
                    skip = "没有可同步的域名"
        items.append(
            PanelSitePreview(
                key=site.key,
                name=site.name,
                domains=site.domains,
                origin_http_port=http_port,
                origin_https_port=https_port,
                has_ssl=site.has_ssl,
                ssl_not_after=site.ssl_not_after,
                force_https=site.force_https,
                already_imported=already,
                skip_reason=skip,
            )
        )
    return items


async def preview_certificates(
    db: AsyncSession,
    row: PanelConnection,
    *,
    replace_certificate_id: int | None = None,
) -> list[PanelCertPreview]:
    """List panel certificates and mark which ones can be imported or used to replace.

    Args:
        db: Database session.
        row: Saved panel connection.
        replace_certificate_id: When set, only the matching domain set is selectable
            so the caller can overwrite that local certificate.

    Returns:
        Preview rows for the panel UI.

    Raises:
        PanelError: If replace_certificate_id does not exist.
    """
    adapter = adapter_for(row)
    raw_certs = await adapter.list_certificates()
    target_set: set[str] | None = None
    existing_sets: list[set[str]] = []
    if replace_certificate_id is not None:
        target = await db.get(Certificate, replace_certificate_id)
        if target is None:
            raise PanelError("证书不存在")
        target_set = _domains_set(target.domains)
    else:
        existing = (await db.execute(select(Certificate))).scalars().all()
        existing_sets = [_domains_set(cert.domains) for cert in existing]
    items: list[PanelCertPreview] = []
    for cert in raw_certs:
        skip = cert.skip_reason
        already = False
        domain_set = _domains_set(cert.domains)
        if target_set is not None:
            if not domain_set or domain_set != target_set:
                skip = skip or "与当前证书域名不一致"
        elif domain_set and any(domain_set == other and other for other in existing_sets):
            already = True
            skip = skip or "相同域名的证书已导入"
        items.append(
            PanelCertPreview(
                key=cert.key,
                name=cert.name,
                domains=cert.domains,
                not_after=cert.not_after,
                already_imported=already,
                skip_reason=skip,
            )
        )
    return items


async def _upsert_cert_from_pem(
    db: AsyncSession,
    pair: PemPair,
    fingerprints: dict[str, Certificate],
) -> Certificate:
    digest = leaf_sha256(pair.cert_pem)
    existing = fingerprints.get(digest)
    if existing is not None:
        return existing
    cert = await persist_new_certificate(
        db,
        name=pair.name,
        cert_content=pair.cert_pem,
        key_content=pair.key_pem,
        remark="从外部面板导入",
        commit=False,
    )
    fingerprints[digest] = cert
    return cert


async def import_sites(
    db: AsyncSession,
    row: PanelConnection,
    keys: list[str],
    *,
    origin_host: str | None = None,
    origin_http_port: int | None = None,
    origin_https_port: int | None = None,
) -> PanelImportResult:
    adapter = adapter_for(row)
    raw_sites = await adapter.list_sites()
    by_key = {item.key: item for item in raw_sites}
    wanted = list(dict.fromkeys(keys))
    fingerprints = await fingerprint_map(db)
    result = PanelImportResult()
    created_any = False
    host = origin_host or default_origin_host(row.panel_url, same_server=bool(row.same_server))
    try:
        host = validate_origin_host(host)
    except ValueError as exc:
        raise PanelError(str(exc)) from exc

    for key in wanted:
        site = by_key.get(key)
        if site is None:
            result.failed.append(
                PanelImportItemResult(key=key, status="failed", reason="面板中未找到该站点")
            )
            continue
        try:
            item = await _import_one_site(
                db,
                adapter=adapter,
                row=row,
                site=site,
                fingerprints=fingerprints,
                origin_host=host,
                origin_http_port=origin_http_port,
                origin_https_port=origin_https_port,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("import site %s failed", key)
            result.failed.append(
                PanelImportItemResult(
                    key=key, name=site.name, status="failed", reason=str(exc)
                )
            )
            continue
        if item.status == "imported":
            created_any = True
            result.imported.append(item)
        elif item.status == "skipped":
            result.skipped.append(item)
        else:
            result.failed.append(item)

    await db.commit()
    if created_any:
        reload_ok = await _sync(db)
        if not reload_ok:
            result.warning = "站点已导入，但引擎重载失败，请稍后在站点管理中保存一次以重新下发"
    return result


async def _import_one_site(
    db: AsyncSession,
    *,
    adapter,
    row: PanelConnection,
    site: RawPanelSite,
    fingerprints: dict[str, Certificate],
    origin_host: str,
    origin_http_port: int | None,
    origin_https_port: int | None,
) -> PanelImportItemResult:
    if site.skip_reason:
        return PanelImportItemResult(
            key=site.key, name=site.name, status="skipped", reason=site.skip_reason
        )
    try:
        domains = normalize_domain_list(site.domains)
        await ensure_domains_available(db, domains)
    except ValueError as exc:
        return PanelImportItemResult(
            key=site.key, name=site.name, status="skipped", reason=str(exc)
        )

    http_port, https_port = remap_listen_ports(
        site.http_port, site.https_port, same_server=bool(row.same_server)
    )
    if origin_http_port is not None:
        http_port = origin_http_port
    if origin_https_port is not None:
        https_port = origin_https_port

    certificate_id = None
    force_https = bool(site.force_https)
    listen_https = False
    try:
        pair = await adapter.fetch_site_cert(site.key)
    except PanelError as exc:
        pair = None
        log.warning("fetch site cert %s: %s", site.key, exc)
    except Exception as exc:  # noqa: BLE001
        pair = None
        log.warning("fetch site cert %s failed: %s", site.key, exc)

    try:
        async with db.begin_nested():
            if pair is not None:
                cert = await _upsert_cert_from_pem(db, pair, fingerprints)
                certificate_id = cert.id
                listen_https = True
                force_https = bool(getattr(pair, "force_https", force_https))
            if not listen_https:
                force_https = False
                certificate_id = None
            record = Site(
                name=site.name[:128],
                origin_host=origin_host,
                origin_protocol="follow",
                origin_http_port=http_port,
                origin_https_port=https_port,
                listen_http=True,
                listen_https=listen_https,
                force_https=force_https,
                disable_content_buffering=bool(row.same_server),
                certificate_id=certificate_id,
                enabled=True,
            )
            apply_domains_to_site(record, domains)
            db.add(record)
            await db.flush()
    except ValueError as exc:
        return PanelImportItemResult(
            key=site.key,
            name=site.name,
            status="failed",
            reason=f"证书无效：{exc}",
        )

    return PanelImportItemResult(
        key=site.key,
        name=site.name,
        status="imported",
        site_id=record.id,
        certificate_id=certificate_id,
    )


async def import_certificates(
    db: AsyncSession,
    row: PanelConnection,
    keys: list[str],
    *,
    replace_certificate_id: int | None = None,
) -> PanelImportResult:
    """Import panel certificates, or overwrite one local certificate in replace mode.

    Args:
        db: Database session.
        row: Saved panel connection.
        keys: Panel certificate keys to import.
        replace_certificate_id: When set, fetch exactly one PEM and overwrite that row.

    Returns:
        Imported / skipped / failed item lists.

    Raises:
        PanelError: If replace mode receives multiple keys, or the target certificate
            does not exist.
    """
    if replace_certificate_id is not None:
        return await _import_certificate_replace(db, row, keys, replace_certificate_id)
    adapter = adapter_for(row)
    fingerprints = await fingerprint_map(db)
    result = PanelImportResult()
    created_any = False
    for key in dict.fromkeys(keys):
        try:
            pair = await adapter.fetch_cert(key)
            digest = leaf_sha256(pair.cert_pem)
            existing = fingerprints.get(digest)
            if existing is not None:
                result.skipped.append(
                    PanelImportItemResult(
                        key=key,
                        name=pair.name,
                        status="skipped",
                        reason="相同证书已导入",
                        certificate_id=existing.id,
                    )
                )
                continue
            async with db.begin_nested():
                cert = await persist_new_certificate(
                    db,
                    name=pair.name,
                    cert_content=pair.cert_pem,
                    key_content=pair.key_pem,
                    remark="从外部面板导入",
                    commit=False,
                )
            fingerprints[digest] = cert
            created_any = True
            result.imported.append(
                PanelImportItemResult(
                    key=key,
                    name=pair.name,
                    status="imported",
                    certificate_id=cert.id,
                )
            )
        except PanelError as exc:
            result.failed.append(
                PanelImportItemResult(key=key, status="failed", reason=str(exc))
            )
        except ValueError as exc:
            result.failed.append(
                PanelImportItemResult(key=key, status="failed", reason=str(exc))
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("import cert %s failed", key)
            result.failed.append(
                PanelImportItemResult(key=key, status="failed", reason=str(exc))
            )
    await db.commit()
    if created_any:
        reload_ok = await _sync(db)
        if not reload_ok:
            result.warning = "证书已导入，但引擎重载失败"
    return result


async def _import_certificate_replace(
    db: AsyncSession,
    row: PanelConnection,
    keys: list[str],
    replace_certificate_id: int,
) -> PanelImportResult:
    """Overwrite one local certificate with a single PEM fetched from the panel.

    Args:
        db: Database session.
        row: Saved panel connection.
        keys: Selected panel keys; must contain exactly one unique key.
        replace_certificate_id: Local certificate id to overwrite.

    Returns:
        Result with one imported, skipped, or failed item.

    Raises:
        PanelError: If more than one key is selected, or the target does not exist.
    """
    wanted = list(dict.fromkeys(keys))
    result = PanelImportResult()
    if len(wanted) != 1:
        raise PanelError("更新证书时只能选择 1 项")
    key = wanted[0]
    target = await db.get(Certificate, replace_certificate_id)
    if target is None:
        raise PanelError("证书不存在")
    adapter = adapter_for(row)
    try:
        pair = await adapter.fetch_cert(key)
        cert_obj, _unused_key = certificate_store.validate_pem_pair(
            pair.cert_pem, pair.key_pem
        )
        meta = certificate_store.parse_cert_meta(cert_obj)
        pem_set = _domains_set(meta["domains"])
        target_set = _domains_set(target.domains)
        if not pem_set or pem_set != target_set:
            result.failed.append(
                PanelImportItemResult(
                    key=key,
                    name=pair.name,
                    status="failed",
                    reason="与当前证书域名不一致",
                )
            )
            return result
        digest = leaf_sha256(pair.cert_pem)
        try:
            existing_pem, _unused = certificate_store.read_cert_files(
                target.cert_path, target.key_path
            )
            if leaf_sha256(existing_pem) == digest:
                result.skipped.append(
                    PanelImportItemResult(
                        key=key,
                        name=pair.name,
                        status="skipped",
                        reason="证书内容未变化",
                        certificate_id=target.id,
                    )
                )
                return result
        except Exception:  # noqa: BLE001
            pass
        apply_pem_to_certificate(target, pair.cert_pem, pair.key_pem)
        await db.commit()
        reload_ok = await reload_sites_using_certificate(db, target.id)
        if not reload_ok:
            result.warning = "证书已更新，但引擎重载失败"
        result.imported.append(
            PanelImportItemResult(
                key=key,
                name=pair.name,
                status="imported",
                certificate_id=target.id,
            )
        )
    except PanelError as exc:
        result.failed.append(
            PanelImportItemResult(key=key, status="failed", reason=str(exc))
        )
    except ValueError as exc:
        result.failed.append(
            PanelImportItemResult(key=key, status="failed", reason=str(exc))
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("replace cert %s failed", key)
        result.failed.append(
            PanelImportItemResult(key=key, status="failed", reason=str(exc))
        )
    return result


async def _sync(db: AsyncSession) -> bool:
    try:
        await rule_sync.publish(db)
        result = await nginx_conf.regenerate(db)
        return bool(getattr(result, "ok", result))
    except Exception as exc:  # noqa: BLE001
        log.exception("panel import sync failed: %s", exc)
        return False
