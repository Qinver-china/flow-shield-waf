"""Let's Encrypt / ZeroSSL HTTP-01 issue and renew (process-wide lock)."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Certificate, Site
from app.models.notification import NotificationChannel
from app.services.certificate_ops import (
    apply_pem_to_certificate,
    persist_new_certificate,
    reload_sites_using_certificate,
)
from app.services.notifications.certificate_expiry import (
    NOTIFY_LOCAL_HOUR,
    days_until_expiry,
)
from app.services.notifications.channels import send_via_channel
from app.services.notifications.email_templates import build_acme_result_email
from app.services.site_domains import normalize_domain_list, site_domain_list
from app.services.traffic_intel.timezone import get_traffic_timezone, local_datetime
from app.services import waf_settings

log = logging.getLogger("waf.acme")

PROVIDER_LETSENCRYPT = "letsencrypt"
PROVIDER_ZEROSSL = "zerossl"
PROVIDERS = (PROVIDER_LETSENCRYPT, PROVIDER_ZEROSSL)
PROVIDER_LABELS = {
    PROVIDER_LETSENCRYPT: "Let's Encrypt",
    PROVIDER_ZEROSSL: "ZeroSSL",
}
DIRECTORY_URLS = {
    PROVIDER_LETSENCRYPT: "https://acme-v02.api.letsencrypt.org/directory",
    PROVIDER_ZEROSSL: "https://acme.zerossl.com/v2/DV90",
}
ZEROSSL_EAB_URL = "https://api.zerossl.com/acme/eab-credentials-email"
USER_AGENT = "FlowShield-WAF"
RENEW_DAYS_BEFORE = 10
_ISSUE_LOCK = asyncio.Lock()

ProgressCallback = Callable[[str], Awaitable[None] | None]
T = TypeVar("T")


class AcmeIssueError(Exception):
    """User-visible ACME issue or renew failure."""


async def _emit_progress(on_progress: ProgressCallback | None, message: str) -> None:
    if not on_progress:
        return
    result = on_progress(message)
    if asyncio.iscoroutine(result):
        await result
    elif hasattr(result, "__await__"):
        await result  # type: ignore[misc]


async def _to_thread_with_progress(
    fn: Callable[..., T],
    /,
    *args,
    on_progress: ProgressCallback | None,
    **kwargs,
) -> T:
    """Run blocking fn in a thread while forwarding sync progress into async callback."""
    if not on_progress:
        return await asyncio.to_thread(fn, *args, **kwargs)

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def sync_progress(message: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, message)

    async def consumer() -> None:
        while True:
            item = await queue.get()
            if item is None:
                return
            await _emit_progress(on_progress, item)

    consumer_task = asyncio.create_task(consumer())
    try:
        return await asyncio.to_thread(fn, *args, on_progress=sync_progress, **kwargs)
    finally:
        loop.call_soon_threadsafe(queue.put_nowait, None)
        await consumer_task


def http01_dir() -> Path:
    return Path(settings.data_dir) / "acme" / "http-01"


def account_dir(provider: str) -> Path:
    return Path(settings.data_dir) / "acme" / provider


def ensure_http01_dir() -> Path:
    path = http01_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def provider_label(provider: str | None) -> str:
    if not provider:
        return "手工导入"
    return PROVIDER_LABELS.get(provider, provider)


def parse_cert_domains(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip().lower() for part in value.split(",") if part.strip()]


def domain_set(value: str | None) -> set[str]:
    return set(parse_cert_domains(value))


def _is_ip_host(value: str) -> bool:
    raw = value.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    try:
        ipaddress.ip_address(raw)
        return True
    except ValueError:
        return False


def normalize_issue_domains(site: Site, domains: list[str]) -> list[str]:
    """Return ACME-eligible domains that belong to the site.

    Args:
        site: Saved site whose server_name list is the allow-list.
        domains: User-selected names (SAN).

    Returns:
        Normalized unique domain list.

    Raises:
        ValueError: Empty, wildcard, IP, or not a subset of the site.
    """
    requested = normalize_domain_list(domains)
    allowed = {item.lower() for item in site_domain_list(site)}
    for domain in requested:
        if "*" in domain:
            raise ValueError("HTTP-01 不支持通配符证书，请勾选具体域名")
        if _is_ip_host(domain):
            raise ValueError(f"免费证书不支持 IP 地址：{domain}")
        if domain not in allowed:
            raise ValueError(f"域名不属于该站点：{domain}")
    return requested


def should_attempt_renew(
    *,
    auto_renew: bool,
    provider: str | None,
    not_after: datetime | None,
    last_attempt_on: str | None,
    now_utc: datetime,
    timezone_name: str,
) -> bool:
    """True when an ACME cert should be renewed this local day (after 10:00)."""
    if not auto_renew or not provider or not_after is None:
        return False
    now_local = local_datetime(now_utc, timezone_name)
    if now_local.hour < NOTIFY_LOCAL_HOUR:
        return False
    today = now_local.date().isoformat()
    if last_attempt_on == today:
        return False
    days_left = days_until_expiry(
        not_after_utc=not_after,
        now_utc=now_utc,
        timezone_name=timezone_name,
    )
    return days_left <= RENEW_DAYS_BEFORE


def friendly_acme_error(exc: BaseException) -> str:
    """Map CA / network exceptions to a short Chinese message."""
    if isinstance(exc, AcmeIssueError):
        return str(exc)
    text = str(exc).strip() or exc.__class__.__name__
    low = text.lower()
    if "rate" in low and "limit" in low:
        return "证书机构请求过于频繁（已达限额），请稍后再试"
    if "unauthorized" in low or "incorrect validations" in low:
        return "HTTP-01 验证失败：请确认域名 A/AAAA 已指向本机，且公网可访问 80 端口"
    if "timeout" in low or "timed out" in low:
        return "连接证书机构或验证超时：请确认本机 80 端口可从公网访问"
    if "nxdomain" in low or "dns problem" in low:
        return "域名解析失败：请确认 A/AAAA 已指向本机"
    if "connection refused" in low or "network is unreachable" in low:
        return "无法完成验证：请确认公网可访问本机 80 端口"
    if len(text) > 300:
        text = text[:300] + "…"
    return f"证书申请失败：{text}"


def _write_challenge(token: str, key_authorization: str) -> Path:
    directory = ensure_http01_dir()
    path = directory / token
    path.write_text(key_authorization, encoding="utf-8")
    return path


def _remove_challenge(token: str) -> None:
    path = http01_dir() / token
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        log.warning("remove ACME challenge %s failed: %s", token, exc)


def _new_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _pem_private_key(key) -> str:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def _load_or_create_account_key(provider: str, jose):
    directory = account_dir(provider)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "account_key.pem"
    if path.is_file():
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    else:
        key = _new_rsa_key()
        path.write_bytes(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    return jose.JWKRSA(key=key)


def _zerossl_eab(email: str, provider: str) -> tuple[str, str]:
    import httpx

    cache = account_dir(provider) / "eab.json"
    if cache.is_file():
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            if (
                cached.get("email") == email
                and cached.get("eab_kid")
                and cached.get("eab_hmac_key")
            ):
                return str(cached["eab_kid"]), str(cached["eab_hmac_key"])
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    resp = httpx.post(
        ZEROSSL_EAB_URL,
        data={"email": email},
        timeout=30.0,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        payload = resp.json()
    except ValueError as exc:
        raise AcmeIssueError("ZeroSSL EAB 接口返回无效内容") from exc
    if not resp.is_success or not payload.get("success", True):
        detail = payload.get("error") or payload.get("message") or resp.text[:200]
        raise AcmeIssueError(f"获取 ZeroSSL EAB 凭证失败：{detail}")
    kid = payload.get("eab_kid") or payload.get("kid")
    hmac_key = payload.get("eab_hmac_key") or payload.get("hmac_key")
    if not kid or not hmac_key:
        raise AcmeIssueError("ZeroSSL EAB 凭证不完整，请稍后重试")
    account_dir(provider).mkdir(parents=True, exist_ok=True)
    cache.write_text(
        json.dumps({"email": email, "eab_kid": kid, "eab_hmac_key": hmac_key}),
        encoding="utf-8",
    )
    return str(kid), str(hmac_key)


def request_certificate_pem(
    provider: str,
    email: str,
    domains: list[str],
    on_progress: Callable[[str], None] | None = None,
) -> tuple[str, str]:
    """Blocking ACME HTTP-01 issue. Returns (fullchain_pem, private_key_pem).

    Args:
        provider: ``letsencrypt`` or ``zerossl``.
        email: ACME account contact email.
        domains: SAN DNS names (no wildcards).
        on_progress: Optional sync callback for step messages.

    Returns:
        PEM full chain and matching private key.

    Raises:
        AcmeIssueError: Validation, rate limit, or CA failure.
    """
    if provider not in PROVIDERS:
        raise AcmeIssueError("不支持的证书机构")
    if not email:
        raise AcmeIssueError("请先在系统设置中填写 ACME 账户邮箱")
    if not domains:
        raise AcmeIssueError("请选择至少一个域名")

    def progress(message: str) -> None:
        if on_progress:
            on_progress(message)

    try:
        from acme import challenges, client, crypto_util, errors, messages
        import josepy as jose
    except ImportError as exc:
        raise AcmeIssueError("服务器未安装 ACME 组件，请升级后重试") from exc

    tokens: list[str] = []
    try:
        progress(f"连接 {provider_label(provider)} …")
        account_key = _load_or_create_account_key(provider, jose)
        net = client.ClientNetwork(account_key, user_agent=USER_AGENT, timeout=30)
        directory = client.ClientV2.get_directory(DIRECTORY_URLS[provider], net)
        acme = client.ClientV2(directory, net)

        extra: dict = {}
        if provider == PROVIDER_ZEROSSL:
            progress("获取 ZeroSSL EAB 凭证…")
            kid, hmac_key = _zerossl_eab(email, provider)
            extra["external_account_binding"] = messages.ExternalAccountBinding.from_data(
                account_public_key=account_key,
                kid=kid,
                hmac_key=hmac_key,
                directory=directory,
            )
        new_reg = messages.NewRegistration.from_data(
            email=email,
            terms_of_service_agreed=True,
            **extra,
        )
        progress("注册或复用 ACME 账户…")
        try:
            regr = acme.new_account(new_reg)
        except errors.ConflictError as err:
            # Account already exists for this key; query by Location URI.
            regr = messages.RegistrationResource(
                body=messages.Registration(),
                uri=err.location,
            )
            regr = acme.query_registration(regr)
        net.account = regr

        progress("生成密钥与证书签名请求…")
        pkey = _new_rsa_key()
        key_pem = _pem_private_key(pkey)
        csr_pem = crypto_util.make_csr(key_pem.encode("utf-8"), domains, must_staple=False)
        order = acme.new_order(csr_pem)

        progress(f"写入 HTTP-01 挑战文件（{', '.join(domains)}）…")
        for authz in order.authorizations:
            http_challenges = [
                challb
                for challb in authz.body.challenges
                if isinstance(challb.chall, challenges.HTTP01)
            ]
            if not http_challenges:
                raise AcmeIssueError("证书机构未提供 HTTP-01 验证，无法继续")
            challb = http_challenges[0]
            response, validation = challb.response_and_validation(account_key)
            token = challb.chall.encode("token")
            tokens.append(token)
            _write_challenge(token, validation)
            acme.answer_challenge(challb, response)

        progress("等待证书机构验证域名并签发…")
        finalized = acme.poll_and_finalize(order)
        cert_pem = finalized.fullchain_pem
        if not cert_pem:
            raise AcmeIssueError("证书机构未返回证书内容")
        progress("证书机构已签发，正在下载证书链…")
        return cert_pem, key_pem
    except AcmeIssueError:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("ACME issue failed provider=%s domains=%s", provider, domains)
        raise AcmeIssueError(friendly_acme_error(exc)) from exc
    finally:
        for token in tokens:
            _remove_challenge(token)


async def _load_channels(db: AsyncSession, channel_ids: list[int]) -> list[NotificationChannel]:
    if not channel_ids:
        return []
    unique_ids = list(dict.fromkeys(int(cid) for cid in channel_ids if cid is not None))
    if not unique_ids:
        return []
    return list(
        (
            await db.execute(
                select(NotificationChannel).where(
                    NotificationChannel.id.in_(unique_ids),
                    NotificationChannel.enabled.is_(True),
                )
            )
        ).scalars().all()
    )


async def notify_acme_result(
    db: AsyncSession,
    channel_ids: list[int],
    *,
    success: bool,
    kind: str,
    cert_name: str,
    domains: str,
    provider: str | None,
    error: str | None = None,
) -> None:
    """Send issue/renew success or failure through configured channels."""
    channels = await _load_channels(db, channel_ids)
    if not channels:
        return
    ca_name = provider_label(provider)
    action = "续期" if kind == "renew" else "申请"
    if success:
        subject = f"流盾WAF 证书{action}成功：{cert_name}"
    else:
        subject = f"流盾WAF 证书{action}失败：{cert_name}"
    plain, html_body = build_acme_result_email(
        success=success,
        kind=kind,
        cert_name=cert_name,
        domains=domains,
        ca_name=ca_name,
        error=error,
    )
    for channel in channels:
        try:
            await send_via_channel(channel, subject=subject, body=plain, html_body=html_body)
        except Exception:  # noqa: BLE001
            log.exception("ACME notify failed channel=%s cert=%s", channel.id, cert_name)


def _default_cert_name(provider: str, domains: list[str]) -> str:
    label = provider_label(provider)
    primary = domains[0] if domains else "certificate"
    name = f"{label} · {primary}"
    return name[:128]


async def _bind_site_certificate(db: AsyncSession, site: Site, cert: Certificate) -> None:
    site.certificate_id = cert.id
    if not site.listen_https:
        site.listen_https = True


async def ensure_acme_http_ready(db: AsyncSession) -> None:
    """Regenerate site nginx so ACME HTTP-01 locations exist before CA validation.

    Args:
        db: Database session used to load sites for conf generation.

    Raises:
        AcmeIssueError: When engine conf regenerate fails.
    """
    from app.services import nginx_conf

    ensure_http01_dir()
    try:
        result = await nginx_conf.regenerate(db)
    except Exception as exc:  # noqa: BLE001
        log.exception("ACME nginx regenerate failed before challenge")
        raise AcmeIssueError(
            f"无法刷新引擎配置以准备证书验证：{friendly_acme_error(exc)}"
        ) from exc
    if not getattr(result, "ok", result):
        detail = (getattr(result, "detail", None) or getattr(result, "reason", None) or "未知错误")
        detail = str(detail).strip() or "未知错误"
        raise AcmeIssueError(f"无法刷新引擎配置以准备证书验证：{detail}")


async def issue_for_site(
    db: AsyncSession,
    *,
    site_id: int,
    domains: list[str],
    provider: str,
    auto_renew: bool,
    expiry_notify_channel_ids: list[int],
    name: str | None = None,
    replace_certificate_id: int | None = None,
    on_progress: ProgressCallback | None = None,
) -> Certificate:
    """Issue an ACME certificate, persist it, bind the site, and notify.

    Args:
        db: Database session.
        site_id: Saved site to bind.
        domains: SAN names; must be a subset of the site domains.
        provider: ``letsencrypt`` or ``zerossl``.
        auto_renew: Daily renew when within 10 days of expiry.
        expiry_notify_channel_ids: Notify channels (required when auto_renew).
        name: Optional certificate display name.
        replace_certificate_id: Overwrite this row instead of creating.
        on_progress: Optional async/sync callback for UI progress lines.

    Returns:
        Persisted certificate row.

    Raises:
        AcmeIssueError: Validation or CA failure (failure is also notified).
    """
    await _emit_progress(on_progress, "校验申请参数…")
    if provider not in PROVIDERS:
        raise AcmeIssueError("不支持的证书机构")
    channel_ids = list(dict.fromkeys(int(cid) for cid in expiry_notify_channel_ids if cid is not None))
    if auto_renew and not channel_ids:
        raise AcmeIssueError("开启自动更新时请选择通知通道")

    setting = await waf_settings.get_or_create(db)
    email = (getattr(setting, "acme_account_email", None) or "").strip()
    if not email:
        raise AcmeIssueError("请先在系统设置 → 显示设置中填写 ACME 账户邮箱")

    site = await db.get(Site, site_id)
    if site is None:
        raise AcmeIssueError("站点不存在")
    try:
        names = normalize_issue_domains(site, domains)
    except ValueError as exc:
        raise AcmeIssueError(str(exc)) from exc

    target: Certificate | None = None
    if replace_certificate_id is not None:
        target = await db.get(Certificate, replace_certificate_id)
        if target is None:
            raise AcmeIssueError("证书不存在")
    elif site.certificate_id:
        bound = await db.get(Certificate, site.certificate_id)
        if (
            bound is not None
            and bound.acme_provider
            and domain_set(bound.domains) == set(names)
        ):
            target = bound

    display_name = (name or "").strip() or (
        target.name if target is not None else _default_cert_name(provider, names)
    )
    domain_label = ", ".join(names)

    async with _ISSUE_LOCK:
        try:
            await _emit_progress(on_progress, "刷新引擎配置，准备 HTTP-01 挑战路径…")
            await ensure_acme_http_ready(db)
            cert_pem, key_pem = await _to_thread_with_progress(
                request_certificate_pem,
                provider,
                email,
                names,
                on_progress=on_progress,
            )
        except Exception as exc:  # noqa: BLE001
            err = friendly_acme_error(exc)
            await notify_acme_result(
                db,
                channel_ids,
                success=False,
                kind="issue",
                cert_name=display_name,
                domains=domain_label,
                provider=provider,
                error=err,
            )
            raise AcmeIssueError(err) from exc

        await _emit_progress(on_progress, "写入证书文件并绑定站点…")
        timezone_name = await get_traffic_timezone(db)
        today = local_datetime(datetime.utcnow(), timezone_name).date().isoformat()
        if target is None:
            cert = await persist_new_certificate(
                db,
                name=display_name,
                cert_content=cert_pem,
                key_content=key_pem,
                expiry_notify_enabled=False,
                expiry_notify_channel_ids=channel_ids,
                commit=False,
            )
        else:
            apply_pem_to_certificate(target, cert_pem, key_pem)
            cert = target
            cert.name = display_name[:128]
            # Do not wipe existing notify channels when re-issue omits them
            # (auto_renew off + empty list from the ACME tab).
        cert.acme_provider = provider
        cert.acme_auto_renew = bool(auto_renew)
        cert.acme_last_attempt_on = today
        cert.acme_last_error = None
        if channel_ids:
            cert.expiry_notify_channel_ids = channel_ids
        await _bind_site_certificate(db, site, cert)
        await db.commit()
        await db.refresh(cert)
        await _emit_progress(on_progress, "重载引擎配置…")
        await reload_sites_using_certificate(db, cert.id)
        await _emit_progress(on_progress, "发送结果通知…")
        await notify_acme_result(
            db,
            channel_ids,
            success=True,
            kind="issue",
            cert_name=cert.name,
            domains=cert.domains or domain_label,
            provider=provider,
        )
        await _emit_progress(on_progress, "申请完成")
        return cert


async def renew_one(
    db: AsyncSession,
    cert: Certificate,
    *,
    timezone_name: str,
    today: str,
    email: str,
) -> bool:
    """Re-issue one ACME certificate in place. Marks today attempted even on failure.

    Args:
        db: Database session.
        cert: ACME certificate with auto-renew enabled.
        timezone_name: Display timezone (unused except logging).
        today: Local YYYY-MM-DD already computed by the worker.
        email: ACME account email.

    Returns:
        True when PEM was replaced successfully.
    """
    del timezone_name
    names = parse_cert_domains(cert.domains)
    provider = cert.acme_provider or ""
    channel_ids = [int(cid) for cid in (cert.expiry_notify_channel_ids or []) if cid is not None]
    if not names or provider not in PROVIDERS:
        cert.acme_last_attempt_on = today
        cert.acme_last_error = "缺少域名或证书机构，无法续期"
        await db.commit()
        await notify_acme_result(
            db,
            channel_ids,
            success=False,
            kind="renew",
            cert_name=cert.name,
            domains=cert.domains or "",
            provider=provider,
            error=cert.acme_last_error,
        )
        return False

    async with _ISSUE_LOCK:
        try:
            await ensure_acme_http_ready(db)
            cert_pem, key_pem = await asyncio.to_thread(
                request_certificate_pem, provider, email, names
            )
            apply_pem_to_certificate(cert, cert_pem, key_pem)
            cert.acme_last_attempt_on = today
            cert.acme_last_error = None
            await db.commit()
            await reload_sites_using_certificate(db, cert.id)
            await notify_acme_result(
                db,
                channel_ids,
                success=True,
                kind="renew",
                cert_name=cert.name,
                domains=cert.domains or ", ".join(names),
                provider=provider,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            err = friendly_acme_error(exc)
            log.warning("ACME renew failed id=%s: %s", cert.id, err)
            cert.acme_last_attempt_on = today
            cert.acme_last_error = err[:512]
            await db.commit()
            await notify_acme_result(
                db,
                channel_ids,
                success=False,
                kind="renew",
                cert_name=cert.name,
                domains=cert.domains or ", ".join(names),
                provider=provider,
                error=err,
            )
            return False


async def run_acme_renewals(db: AsyncSession) -> int:
    """Renew due ACME certificates once per local day. Returns success count."""
    timezone_name = await get_traffic_timezone(db)
    now_utc = datetime.utcnow()
    now_local = local_datetime(now_utc, timezone_name)
    if now_local.hour < NOTIFY_LOCAL_HOUR:
        return 0

    setting = await waf_settings.get_or_create(db)
    email = (getattr(setting, "acme_account_email", None) or "").strip()
    today = now_local.date().isoformat()
    rows = (
        await db.execute(
            select(Certificate).where(
                Certificate.acme_auto_renew.is_(True),
                Certificate.acme_provider.is_not(None),
                Certificate.not_after.is_not(None),
            )
        )
    ).scalars().all()

    succeeded = 0
    for cert in rows:
        if not should_attempt_renew(
            auto_renew=bool(cert.acme_auto_renew),
            provider=cert.acme_provider,
            not_after=cert.not_after,
            last_attempt_on=cert.acme_last_attempt_on,
            now_utc=now_utc,
            timezone_name=timezone_name,
        ):
            continue
        if not email:
            cert.acme_last_attempt_on = today
            cert.acme_last_error = "未配置 ACME 账户邮箱，无法续期"
            await db.commit()
            channel_ids = [
                int(cid) for cid in (cert.expiry_notify_channel_ids or []) if cid is not None
            ]
            await notify_acme_result(
                db,
                channel_ids,
                success=False,
                kind="renew",
                cert_name=cert.name,
                domains=cert.domains or "",
                provider=cert.acme_provider,
                error=cert.acme_last_error,
            )
            continue
        if await renew_one(
            db, cert, timezone_name=timezone_name, today=today, email=email
        ):
            succeeded += 1
    return succeeded
