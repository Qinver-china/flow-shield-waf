"""Shared certificate create / fingerprint helpers."""
from __future__ import annotations

import hashlib
import logging

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Certificate
from app.services import certificate_store

log = logging.getLogger("waf.certificate_ops")


def leaf_sha256(cert_pem: str) -> str:
    chain = x509.load_pem_x509_certificates(cert_pem.encode())
    if not chain:
        raise ValueError("无法解析证书 PEM 内容")
    der = chain[0].public_bytes(Encoding.DER)
    return hashlib.sha256(der).hexdigest()


async def persist_new_certificate(
    db: AsyncSession,
    *,
    name: str,
    cert_content: str,
    key_content: str,
    remark: str | None = None,
    expiry_notify_enabled: bool = False,
    expiry_notify_channel_ids: list[int] | None = None,
    commit: bool = True,
) -> Certificate:
    channel_ids = list(expiry_notify_channel_ids or [])
    if not expiry_notify_enabled:
        channel_ids = []

    cert_obj, _key = certificate_store.validate_pem_pair(cert_content, key_content)
    meta = certificate_store.parse_cert_meta(cert_obj)

    cert = Certificate(
        name=name.strip()[:128],
        domains=meta["domains"],
        cert_path="",
        key_path="",
        not_before=meta["not_before"],
        not_after=meta["not_after"],
        remark=remark,
        expiry_notify_enabled=expiry_notify_enabled,
        expiry_notify_channel_ids=channel_ids,
    )
    db.add(cert)
    await db.flush()

    cert_path, key_path = certificate_store.write_cert_files(
        cert.id, cert_content, key_content
    )
    cert.cert_path = cert_path
    cert.key_path = key_path
    if commit:
        await db.commit()
        await db.refresh(cert)
    return cert


async def fingerprint_map(db: AsyncSession) -> dict[str, Certificate]:
    rows = (await db.execute(select(Certificate))).scalars().all()
    out: dict[str, Certificate] = {}
    for cert in rows:
        try:
            cert_pem, _key = certificate_store.read_cert_files(cert.cert_path, cert.key_path)
            out[leaf_sha256(cert_pem)] = cert
        except Exception as exc:  # noqa: BLE001
            log.warning("skip cert fingerprint id=%s: %s", cert.id, exc)
    return out
