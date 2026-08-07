"""Persist SSL certificate files and parse PEM metadata."""
from __future__ import annotations

import logging
import os
import pwd
import re
import shutil

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_private_key,
)

from app.core.config import settings

log = logging.getLogger("waf.certificate_store")

_CERT_BEGIN = re.compile(r"-----BEGIN CERTIFICATE-----")
_KEY_BEGIN = re.compile(
    r"-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----|-----BEGIN OPENSSH PRIVATE KEY-----"
)


def _normalize_pem(content: str) -> str:
    return content.replace("\r\n", "\n").strip() + "\n"


def _public_keys_match(cert_pub, key_pub) -> bool:
    """Compare public keys across RSA/EC/Ed25519 without relying on public_numbers()."""
    try:
        left = cert_pub.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
        right = key_pub.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
        return left == right
    except Exception:  # noqa: BLE001
        return False


def validate_pem_pair(cert_pem: str, key_pem: str) -> tuple[x509.Certificate, object]:
    cert_pem = _normalize_pem(cert_pem)
    key_pem = _normalize_pem(key_pem)

    if not _CERT_BEGIN.search(cert_pem):
        raise ValueError("证书内容无效，需为 PEM 格式（含 BEGIN CERTIFICATE）")
    if not _KEY_BEGIN.search(key_pem):
        raise ValueError("私钥内容无效，需为 PEM 格式（含 BEGIN PRIVATE KEY）")

    try:
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
    except Exception as exc:  # noqa: BLE001
        raise ValueError("无法解析证书 PEM 内容") from exc

    try:
        key = load_pem_private_key(key_pem.encode(), password=None, backend=default_backend())
    except Exception as exc:  # noqa: BLE001
        raise ValueError("无法解析私钥 PEM 内容（暂不支持加密私钥）") from exc

    key_pub = None
    if isinstance(key, (rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey, ed25519.Ed25519PrivateKey)):
        key_pub = key.public_key()

    if key_pub is None or not _public_keys_match(cert.public_key(), key_pub):
        raise ValueError("证书与私钥不匹配")

    return cert, key


def extract_domains(cert: x509.Certificate) -> str:
    names: list[str] = []
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        names.extend(san.value.get_values_for_type(x509.DNSName))
    except x509.ExtensionNotFound:
        pass

    for attr in cert.subject:
        if attr.oid == x509.oid.NameOID.COMMON_NAME:
            cn = attr.value
            if cn and cn not in names:
                names.insert(0, cn)
            break

    return ", ".join(names)


def cert_dir(cert_id: int) -> str:
    return os.path.join(settings.engine_cert_dir, str(cert_id))


def cert_paths(cert_id: int) -> tuple[str, str]:
    base = cert_dir(cert_id)
    return (
        os.path.join(base, "fullchain.pem"),
        os.path.join(base, "privkey.pem"),
    )


def read_cert_files(cert_path: str, key_path: str) -> tuple[str, str]:
    if not os.path.isfile(cert_path) or not os.path.isfile(key_path):
        raise ValueError("证书文件不存在或已被删除")
    with open(cert_path, encoding="utf-8") as f:
        cert_pem = f.read()
    with open(key_path, encoding="utf-8") as f:
        key_pem = f.read()
    return cert_pem, key_pem


def _nginx_owner() -> tuple[int, int] | None:
    try:
        entry = pwd.getpwnam("nobody")
        return entry.pw_uid, entry.pw_gid
    except KeyError:
        return None


def apply_cert_permissions(base: str, cert_path: str, key_path: str) -> None:
    """Make cert files readable by OpenResty worker (runs as nobody)."""
    os.chmod(base, 0o755)
    os.chmod(cert_path, 0o644)
    owner = _nginx_owner()
    if owner:
        uid, gid = owner
        os.chown(base, uid, gid)
        os.chown(cert_path, uid, gid)
        os.chown(key_path, uid, gid)
        os.chmod(key_path, 0o600)
    else:
        os.chmod(key_path, 0o644)


def write_cert_files(cert_id: int, cert_pem: str, key_pem: str) -> tuple[str, str]:
    cert_pem = _normalize_pem(cert_pem)
    key_pem = _normalize_pem(key_pem)
    base = cert_dir(cert_id)
    os.makedirs(base, mode=0o755, exist_ok=True)

    cert_path, key_path = cert_paths(cert_id)
    with open(cert_path, "w", encoding="utf-8") as f:
        f.write(cert_pem)
    with open(key_path, "w", encoding="utf-8") as f:
        f.write(key_pem)
    apply_cert_permissions(base, cert_path, key_path)
    return cert_path, key_path


def remove_cert_files(cert_id: int) -> None:
    base = cert_dir(cert_id)
    if os.path.isdir(base):
        shutil.rmtree(base, ignore_errors=True)


def parse_cert_meta(cert: x509.Certificate) -> dict:
    not_before = cert.not_valid_before_utc.replace(tzinfo=None)
    not_after = cert.not_valid_after_utc.replace(tzinfo=None)
    return {
        "domains": extract_domains(cert),
        "not_before": not_before,
        "not_after": not_after,
    }


def ensure_cert_dir() -> None:
    os.makedirs(settings.engine_cert_dir, mode=0o755, exist_ok=True)
    repair_all_cert_permissions()


def repair_all_cert_permissions() -> None:
    root = settings.engine_cert_dir
    if not os.path.isdir(root):
        return
    for name in os.listdir(root):
        if not name.isdigit():
            continue
        base = os.path.join(root, name)
        cert_path, key_path = cert_paths(int(name))
        if os.path.isfile(cert_path) and os.path.isfile(key_path):
            apply_cert_permissions(base, cert_path, key_path)
