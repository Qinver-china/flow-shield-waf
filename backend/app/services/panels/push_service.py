"""Push a local certificate PEM onto selected BaoTa / 1Panel websites."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Certificate, PanelConnection
from app.schemas.certificate import normalize_panel_push_targets
from app.services import certificate_store
from app.services.panels.import_service import adapter_for
from app.services.panels.types import PanelError

log = logging.getLogger("waf.panels.push")


def _item(key: str, name: str | None, reason: str | None = None) -> dict[str, Any]:
    return {"key": key, "name": name, "reason": reason}


async def push_certificate_to_panels(
    db: AsyncSession,
    cert: Certificate,
    *,
    targets: list | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Deploy ``cert`` PEM to each configured panel site.

    Args:
        db: Database session used to load panel accounts.
        cert: Certificate whose on-disk PEM should be pushed.
        targets: Optional override of ``cert.panel_push_targets``.

    Returns:
        ``{"pushed": [...], "failed": [...]}`` with per-site results.

    Raises:
        PanelError: If the certificate files cannot be read or no targets exist.
        ValueError: If target JSON is malformed.
    """
    try:
        cert_pem, key_pem = certificate_store.read_cert_files(cert.cert_path, cert.key_path)
    except ValueError as exc:
        raise PanelError(str(exc)) from exc

    normalized = normalize_panel_push_targets(targets if targets is not None else cert.panel_push_targets)
    if not normalized:
        raise PanelError("请选择要同步的面板站点")

    pushed: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for target in normalized:
        connection_id = int(target["connection_id"])
        site_keys = list(target["site_keys"])
        row = await db.get(PanelConnection, connection_id)
        if row is None:
            for site_key in site_keys:
                failed.append(_item(site_key, site_key, "面板账号不存在"))
            continue
        if not row.enabled:
            for site_key in site_keys:
                failed.append(_item(site_key, site_key, "该面板账号已停用"))
            continue
        adapter = adapter_for(row)
        names_by_key: dict[str, str] = {}
        try:
            for site in await adapter.list_sites():
                names_by_key[str(site.key)] = site.name or site.key
        except PanelError as exc:
            log.warning("list panel sites failed connection=%s: %s", connection_id, exc)
        for site_key in site_keys:
            label = names_by_key.get(site_key) or site_key
            try:
                await adapter.push_site_cert(site_key, cert_pem, key_pem)
                pushed.append(_item(site_key, label))
            except PanelError as exc:
                log.warning(
                    "push cert id=%s connection=%s site=%s failed: %s",
                    cert.id,
                    connection_id,
                    site_key,
                    exc,
                )
                failed.append(_item(site_key, label, str(exc)))
            except Exception as exc:  # noqa: BLE001
                log.exception(
                    "push cert id=%s connection=%s site=%s crashed",
                    cert.id,
                    connection_id,
                    site_key,
                )
                failed.append(_item(site_key, label, str(exc)))
    return {"pushed": pushed, "failed": failed}
