"""Export / import WAF configuration as a portable JSON backup."""
from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect as sa_inspect

from app.models import (
    AiGuardPolicy,
    AiGuardSetting,
    AlertPolicy,
    BotCategory,
    BotProfile,
    Certificate,
    Exception_,
    IpGroup,
    IpList,
    NotificationChannel,
    PanelConnection,
    RateLimit,
    Rule,
    Site,
    WafSetting,
)
from app.services import certificate_store, nginx_conf, rule_sync
from app.services.ai_guard.crypto import decrypt_secret, encrypt_secret

log = logging.getLogger("waf.backup")

FORMAT_NAME = "flow-shield-waf-backup"
FORMAT_VERSION = 1

# Top-level section keys shown in the UI (may expand to multiple data bags).
SECTION_DEFS: dict[str, dict[str, Any]] = {
    "sites": {
        "label": "站点",
        "bags": ("sites",),
    },
    "certificates": {
        "label": "证书",
        "bags": ("certificates",),
    },
    "ip_groups": {
        "label": "IP 组",
        "bags": ("ip_groups",),
    },
    "rules": {
        "label": "规则（白/黑名单、自定义、例外、限速）",
        "bags": (
            "rules",
            "blacklist",
            "whitelist",
            "exceptions",
            "ratelimits",
        ),
    },
    "bots": {
        "label": "Bot 库",
        "bags": ("bot_categories", "bots"),
    },
    "ai_config": {
        "label": "AI 配置",
        "bags": ("ai_guard_settings",),
    },
    "ai_policies": {
        "label": "AI 防护策略",
        "bags": ("ai_guard_policies",),
    },
    "system_settings": {
        "label": "系统设置",
        "bags": ("waf_settings", "notification_channels", "alert_policies", "panel_connections"),
    },
}

ALL_SECTIONS = tuple(SECTION_DEFS.keys())

# Older backups used a single "ai_guard" section for both settings + policies.
_LEGACY_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "ai_guard": ("ai_config", "ai_policies"),
}

_SITE_FIELDS = (
    "name",
    "domain",
    "extra_domains",
    "origin_host",
    "origin_protocol",
    "origin_http_port",
    "origin_https_port",
    "client_ip_source",
    "listen_http",
    "listen_https",
    "custom_listen_ports",
    "listen_http_ports",
    "listen_https_ports",
    "force_https",
    "disable_content_buffering",
    "enabled",
    "custom_block_page_enabled",
    "block_page_status_code",
    "block_page_html",
    "custom_captcha_footer_enabled",
    "captcha_footer_html",
)

_RULE_FIELDS = (
    "name",
    "priority",
    "mode",
    "enabled",
    "conditions",
    "remark",
    "custom_block_page_enabled",
    "block_page_status_code",
    "block_page_html",
)

_IPLIST_FIELDS = (
    "name",
    "enabled",
    "conditions",
    "remark",
    "expire_at",
    "custom_block_page_enabled",
    "block_page_status_code",
    "block_page_html",
)

_EXCEPTION_FIELDS = ("name", "scope", "enabled", "conditions", "remark")

_RATELIMIT_FIELDS = (
    "name",
    "priority",
    "enabled",
    "keys",
    "window",
    "threshold",
    "mode",
    "conditions",
    "remark",
    "custom_block_page_enabled",
    "block_page_status_code",
    "block_page_html",
)

_BOT_FIELDS = (
    "name",
    "categories",
    "ua_patterns",
    "enabled",
    "verify_dns_suffix",
    "is_builtin",
    "remark",
)

_AI_POLICY_FIELDS = (
    "name",
    "enabled",
    "trigger_type",
    "trigger_params",
    "apply_mode",
    "notify_on",
    "condition_filter",
    "cooldown_sec",
    "remark",
    "custom_prompt",
)

_CHANNEL_FIELDS = ("name", "channel_type", "enabled", "config", "remark")
_PANEL_CONNECTION_FIELDS = (
    "name",
    "provider",
    "panel_url",
    "api_key",
    "same_server",
    "verify_tls",
    "enabled",
    "remark",
    "extra",
)

_ALERT_FIELDS = (
    "name",
    "enabled",
    "condition_type",
    "condition_params",
    "cooldown_sec",
    "remark",
)

_WAF_SETTING_SKIP = {"id", "created_at", "updated_at"}


def section_catalog() -> list[dict[str, str]]:
    return [{"key": key, "label": meta["label"]} for key, meta in SECTION_DEFS.items()]


def _expand_section_aliases(sections: list[str]) -> list[str]:
    expanded: list[str] = []
    for key in sections:
        aliases = _LEGACY_SECTION_ALIASES.get(key)
        if aliases:
            expanded.extend(aliases)
        else:
            expanded.append(key)
    return expanded


def _normalize_sections(sections: list[str] | None) -> list[str]:
    if not sections:
        return list(ALL_SECTIONS)
    expanded = _expand_section_aliases(sections)
    unknown = [s for s in expanded if s not in SECTION_DEFS]
    if unknown:
        raise ValueError(f"未知导出分区: {', '.join(unknown)}")
    # stable order
    return [s for s in ALL_SECTIONS if s in set(expanded)]


def _serialize_row(obj: Any, *, exclude: set[str] | None = None) -> dict[str, Any]:
    skip = exclude or set()
    out: dict[str, Any] = {}
    for attr in sa_inspect(obj).mapper.column_attrs:
        key = attr.key
        if key in skip:
            continue
        val = getattr(obj, key)
        if isinstance(val, datetime):
            val = val.isoformat()
        out[key] = val
    return out


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def _apply_fields(obj: Any, item: dict[str, Any], fields: tuple[str, ...]) -> None:
    for key in fields:
        if key not in item:
            continue
        val = item[key]
        if key.endswith("_at") or key in {"expire_at", "last_triggered_at", "last_fired_at"}:
            val = _parse_dt(val)
        setattr(obj, key, deepcopy(val) if isinstance(val, (dict, list)) else val)


def _remap_ids(ids: list | None, id_map: dict[int, int]) -> list | None:
    if ids is None:
        return None
    if not isinstance(ids, list):
        return None
    out: list[int] = []
    for raw in ids:
        try:
            old = int(raw)
        except (TypeError, ValueError):
            continue
        new = id_map.get(old)
        if new is not None:
            out.append(new)
    return out


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


async def build_export(db: AsyncSession, sections: list[str] | None = None) -> dict[str, Any]:
    selected = _normalize_sections(sections)
    data: dict[str, Any] = {}

    if "certificates" in selected:
        rows = (await db.execute(select(Certificate).order_by(Certificate.id))).scalars().all()
        certs = []
        for row in rows:
            item = _serialize_row(row, exclude={"cert_path", "key_path"})
            try:
                cert_pem, key_pem = certificate_store.read_cert_files(row.cert_path, row.key_path)
                item["cert_pem"] = cert_pem
                item["key_pem"] = key_pem
            except Exception as exc:  # noqa: BLE001
                log.warning("skip cert pem id=%s: %s", row.id, exc)
                item["cert_pem"] = None
                item["key_pem"] = None
                item["export_error"] = str(exc)
            certs.append(item)
        data["certificates"] = certs

    if "sites" in selected:
        rows = (await db.execute(select(Site).order_by(Site.id))).scalars().all()
        data["sites"] = [_serialize_row(r) for r in rows]

    if "ip_groups" in selected:
        groups = (await db.execute(select(IpGroup).order_by(IpGroup.id))).scalars().all()
        data["ip_groups"] = [_serialize_row(r) for r in groups]

    if "rules" in selected:
        rules = (await db.execute(select(Rule).order_by(Rule.id))).scalars().all()
        data["rules"] = [_serialize_row(r) for r in rules]

        iplists = (await db.execute(select(IpList).order_by(IpList.id))).scalars().all()
        data["blacklist"] = [
            _serialize_row(r) for r in iplists if r.list_type == "black"
        ]
        data["whitelist"] = [
            _serialize_row(r) for r in iplists if r.list_type == "white"
        ]

        exceptions = (await db.execute(select(Exception_).order_by(Exception_.id))).scalars().all()
        data["exceptions"] = [_serialize_row(r) for r in exceptions]

        rates = (await db.execute(select(RateLimit).order_by(RateLimit.id))).scalars().all()
        data["ratelimits"] = [_serialize_row(r) for r in rates]

    if "bots" in selected:
        cats = (await db.execute(select(BotCategory).order_by(BotCategory.id))).scalars().all()
        data["bot_categories"] = [_serialize_row(r) for r in cats]
        bots = (await db.execute(select(BotProfile).order_by(BotProfile.id))).scalars().all()
        data["bots"] = [_serialize_row(r) for r in bots]

    if "ai_config" in selected:
        setting = (
            await db.execute(select(AiGuardSetting).where(AiGuardSetting.id == 1))
        ).scalar_one_or_none()
        if setting:
            item = _serialize_row(setting, exclude={"api_key_encrypted"})
            item["api_key"] = decrypt_secret(setting.api_key_encrypted)
            data["ai_guard_settings"] = item
        else:
            data["ai_guard_settings"] = None

    if "ai_policies" in selected:
        policies = (
            await db.execute(select(AiGuardPolicy).order_by(AiGuardPolicy.id))
        ).scalars().all()
        data["ai_guard_policies"] = [_serialize_row(r) for r in policies]

    if "system_settings" in selected:
        waf = (await db.execute(select(WafSetting).where(WafSetting.id == 1))).scalar_one_or_none()
        data["waf_settings"] = _serialize_row(waf) if waf else None
        channels = (
            await db.execute(select(NotificationChannel).order_by(NotificationChannel.id))
        ).scalars().all()
        data["notification_channels"] = [_serialize_row(r) for r in channels]
        alerts = (
            await db.execute(select(AlertPolicy).order_by(AlertPolicy.id))
        ).scalars().all()
        data["alert_policies"] = [_serialize_row(r) for r in alerts]
        panels = (
            await db.execute(select(PanelConnection).order_by(PanelConnection.id))
        ).scalars().all()
        data["panel_connections"] = [_serialize_row(r) for r in panels]

    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "sections": selected,
        "data": data,
    }


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


async def _find_one(db: AsyncSession, model, *clauses):
    return (await db.execute(select(model).where(*clauses))).scalar_one_or_none()


def _certificate_channel_ids(item: dict[str, Any]) -> list[int]:
    raw = item.get("expiry_notify_channel_ids")
    if raw is None and item.get("expiry_notify_channel_id") is not None:
        raw = [item.get("expiry_notify_channel_id")]
    if not raw:
        return []
    out: list[int] = []
    for value in raw:
        try:
            out.append(int(value))
        except (TypeError, ValueError):
            continue
    return out


def _certificate_domains(item: dict[str, Any], pem_domains: str | None) -> str | None:
    """Prefer exported domains (auto-renew SANs) when present; else PEM metadata."""
    if "domains" not in item:
        return pem_domains
    raw = item.get("domains")
    if raw is None:
        return pem_domains
    text = str(raw).strip()
    return text or pem_domains


def _apply_certificate_acme_fields(cert, item: dict[str, Any]) -> None:
    if "acme_provider" in item:
        provider = item.get("acme_provider")
        cert.acme_provider = str(provider).strip() or None if provider else None
    if "acme_auto_renew" in item:
        cert.acme_auto_renew = bool(item.get("acme_auto_renew"))
    if "acme_last_attempt_on" in item:
        cert.acme_last_attempt_on = item.get("acme_last_attempt_on") or None
    if "acme_last_error" in item:
        cert.acme_last_error = item.get("acme_last_error") or None
    if "panel_push_enabled" in item:
        cert.panel_push_enabled = bool(item.get("panel_push_enabled"))
    if "panel_push_targets" in item:
        cert.panel_push_targets = list(item.get("panel_push_targets") or [])


def _remap_panel_push_targets(
    targets: object, panel_map: dict[int, int]
) -> list[dict[str, Any]]:
    """Rewrite stored panel connection IDs after a backup import.

    Args:
        targets: Exported ``panel_push_targets`` JSON.
        panel_map: Old panel-connection id to newly imported id.

    Returns:
        Targets whose connection still exists after remap.
    """
    out: list[dict[str, Any]] = []
    if not isinstance(targets, list):
        return out
    for item in targets:
        if not isinstance(item, dict):
            continue
        try:
            old_id = int(item.get("connection_id"))
        except (TypeError, ValueError):
            continue
        new_id = panel_map.get(old_id)
        if new_id is None:
            continue
        keys: list[str] = []
        seen: set[str] = set()
        for key in item.get("site_keys") or []:
            site_key = str(key or "").strip()
            if not site_key or site_key in seen:
                continue
            seen.add(site_key)
            keys.append(site_key)
        if not keys:
            continue
        out.append({"connection_id": new_id, "site_keys": keys})
    return out


def _finalize_certificate_panel_push(
    cert, item: dict[str, Any], panel_map: dict[int, int]
) -> None:
    """Remap panel-push connection IDs and drop targets that no longer exist."""
    if "panel_push_targets" not in item and "panel_push_enabled" not in item:
        return
    remapped = _remap_panel_push_targets(getattr(cert, "panel_push_targets", None), panel_map)
    cert.panel_push_targets = remapped
    if not remapped or not bool(getattr(cert, "acme_auto_renew", False)):
        cert.panel_push_enabled = False
        if not bool(getattr(cert, "acme_auto_renew", False)):
            cert.panel_push_targets = []


async def _import_certificates(
    db: AsyncSession,
    items: list[dict[str, Any]],
    channel_map: dict[int, int] | None = None,
    panel_map: dict[int, int] | None = None,
) -> dict[int, int]:
    id_map: dict[int, int] = {}
    channels = channel_map or {}
    panels = panel_map or {}
    for item in items:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        cert_pem = item.get("cert_pem")
        key_pem = item.get("key_pem")
        if not cert_pem or not key_pem:
            log.warning("skip certificate without pem: %s", name)
            continue

        existing = await _find_one(db, Certificate, Certificate.name == name)
        try:
            cert_obj, _ = certificate_store.validate_pem_pair(cert_pem, key_pem)
            meta = certificate_store.parse_cert_meta(cert_obj)
        except ValueError as exc:
            log.warning("invalid certificate %s: %s", name, exc)
            continue

        domains = _certificate_domains(item, meta["domains"])
        channel_ids = _remap_ids(_certificate_channel_ids(item), channels) or []

        if existing:
            existing.domains = domains
            existing.not_before = meta["not_before"]
            existing.not_after = meta["not_after"]
            existing.remark = item.get("remark")
            if "expiry_notify_enabled" in item:
                existing.expiry_notify_enabled = bool(item.get("expiry_notify_enabled"))
            if "expiry_notify_channel_ids" in item or "expiry_notify_channel_id" in item:
                existing.expiry_notify_channel_ids = channel_ids
            _apply_certificate_acme_fields(existing, item)
            _finalize_certificate_panel_push(existing, item, panels)
            paths = certificate_store.write_cert_files(existing.id, cert_pem, key_pem)
            existing.cert_path, existing.key_path = paths
            await db.flush()
            if item.get("id") is not None:
                id_map[int(item["id"])] = existing.id
        else:
            cert = Certificate(
                name=name,
                domains=domains,
                cert_path="",
                key_path="",
                not_before=meta["not_before"],
                not_after=meta["not_after"],
                remark=item.get("remark"),
                expiry_notify_enabled=bool(item.get("expiry_notify_enabled")),
                expiry_notify_channel_ids=channel_ids,
            )
            _apply_certificate_acme_fields(cert, item)
            _finalize_certificate_panel_push(cert, item, panels)
            db.add(cert)
            await db.flush()
            paths = certificate_store.write_cert_files(cert.id, cert_pem, key_pem)
            cert.cert_path, cert.key_path = paths
            await db.flush()
            if item.get("id") is not None:
                id_map[int(item["id"])] = cert.id
    return id_map


async def _import_sites(
    db: AsyncSession,
    items: list[dict[str, Any]],
    cert_map: dict[int, int],
) -> dict[int, int]:
    id_map: dict[int, int] = {}
    for item in items:
        domain = (item.get("domain") or "").strip().lower()
        if not domain:
            continue
        existing = await _find_one(db, Site, Site.domain == domain)
        cert_id = None
        raw_cert = item.get("certificate_id")
        if raw_cert is not None:
            try:
                cert_id = cert_map.get(int(raw_cert))
            except (TypeError, ValueError):
                cert_id = None

        if existing:
            _apply_fields(existing, item, _SITE_FIELDS)
            existing.domain = domain
            existing.certificate_id = cert_id
            await db.flush()
            if item.get("id") is not None:
                id_map[int(item["id"])] = existing.id
        else:
            site = Site(domain=domain, name=item.get("name") or domain, origin_host="127.0.0.1")
            _apply_fields(site, item, _SITE_FIELDS)
            site.domain = domain
            site.certificate_id = cert_id
            db.add(site)
            await db.flush()
            if item.get("id") is not None:
                id_map[int(item["id"])] = site.id
    return id_map


def _remap_ip_group_ids_in_conditions(
    node: Any, group_map: dict[int, int]
) -> Any:
    if not isinstance(node, dict):
        return node
    out = deepcopy(node)
    if "conditions" in out:
        out["conditions"] = [
            _remap_ip_group_ids_in_conditions(child, group_map)
            for child in (out.get("conditions") or [])
        ]
        return out
    op = out.get("op")
    if op in {"in_ip_group", "not_in_ip_group"}:
        value = out.get("value") or []
        if isinstance(value, list):
            remapped: list[int] = []
            for item in value:
                try:
                    old = int(item)
                except (TypeError, ValueError):
                    continue
                new = group_map.get(old)
                if new is not None:
                    remapped.append(new)
            out["value"] = remapped
    return out


async def _import_ip_groups(
    db: AsyncSession, items: list[dict[str, Any]]
) -> dict[int, int]:
    id_map: dict[int, int] = {}
    for item in items:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        existing = await _find_one(db, IpGroup, IpGroup.name == name)
        if existing:
            existing.remark = item.get("remark")
            existing.entries = deepcopy(item.get("entries") or [])
            await db.flush()
            if item.get("id") is not None:
                id_map[int(item["id"])] = existing.id
        else:
            row = IpGroup(
                name=name,
                remark=item.get("remark"),
                entries=deepcopy(item.get("entries") or []),
            )
            db.add(row)
            await db.flush()
            if item.get("id") is not None:
                id_map[int(item["id"])] = row.id
    return id_map


async def _import_named_scoped(
    db: AsyncSession,
    *,
    model,
    items: list[dict[str, Any]],
    fields: tuple[str, ...],
    site_map: dict[int, int],
    group_map: dict[int, int] | None = None,
    extra: dict[str, Any] | None = None,
    name_match_extra=None,
) -> int:
    count = 0
    group_map = group_map or {}
    for item in items:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        clauses = [model.name == name]
        if name_match_extra is not None:
            clauses.append(name_match_extra)
        existing = await _find_one(db, model, *clauses)
        site_ids = _remap_ids(item.get("site_ids"), site_map)
        payload = dict(item)
        if "conditions" in payload and payload["conditions"] is not None:
            payload["conditions"] = _remap_ip_group_ids_in_conditions(
                payload["conditions"], group_map
            )
        if existing:
            _apply_fields(existing, payload, fields)
            existing.site_ids = site_ids
            if extra:
                for k, v in extra.items():
                    setattr(existing, k, v)
        else:
            row = model(name=name)
            if extra:
                for k, v in extra.items():
                    setattr(row, k, v)
            _apply_fields(row, payload, fields)
            row.site_ids = site_ids
            db.add(row)
        count += 1
    await db.flush()
    return count


async def _import_bot_categories(db: AsyncSession, items: list[dict[str, Any]]) -> int:
    count = 0
    for item in items:
        value = (item.get("value") or "").strip()
        if not value:
            continue
        existing = await _find_one(db, BotCategory, BotCategory.value == value)
        if existing:
            existing.label = item.get("label") or existing.label
            existing.sort_order = int(item.get("sort_order") or existing.sort_order or 0)
            existing.remark = item.get("remark")
            # never demote builtin
            if item.get("is_builtin"):
                existing.is_builtin = True
        else:
            db.add(
                BotCategory(
                    value=value,
                    label=item.get("label") or value,
                    sort_order=int(item.get("sort_order") or 0),
                    is_builtin=bool(item.get("is_builtin")),
                    remark=item.get("remark"),
                )
            )
        count += 1
    await db.flush()
    return count


async def _import_bots(
    db: AsyncSession, items: list[dict[str, Any]], site_map: dict[int, int]
) -> int:
    count = 0
    for item in items:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        existing = await _find_one(db, BotProfile, BotProfile.name == name)
        site_ids = _remap_ids(item.get("site_ids"), site_map)
        if existing:
            _apply_fields(existing, item, _BOT_FIELDS)
            existing.site_ids = site_ids
            if item.get("is_builtin"):
                existing.is_builtin = True
        else:
            bot = BotProfile(name=name)
            _apply_fields(bot, item, _BOT_FIELDS)
            bot.site_ids = site_ids
            db.add(bot)
        count += 1
    await db.flush()
    return count


async def _import_channels(
    db: AsyncSession, items: list[dict[str, Any]]
) -> dict[int, int]:
    id_map: dict[int, int] = {}
    for item in items:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        existing = await _find_one(db, NotificationChannel, NotificationChannel.name == name)
        if existing:
            _apply_fields(existing, item, _CHANNEL_FIELDS)
            await db.flush()
            if item.get("id") is not None:
                id_map[int(item["id"])] = existing.id
        else:
            row = NotificationChannel(name=name, channel_type=item.get("channel_type") or "email")
            _apply_fields(row, item, _CHANNEL_FIELDS)
            db.add(row)
            await db.flush()
            if item.get("id") is not None:
                id_map[int(item["id"])] = row.id
    return id_map


async def _import_panel_connections(db: AsyncSession, items: list[dict[str, Any]]) -> dict[int, int]:
    id_map: dict[int, int] = {}
    for item in items:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        existing = await _find_one(db, PanelConnection, PanelConnection.name == name)
        if existing:
            _apply_fields(existing, item, _PANEL_CONNECTION_FIELDS)
            if not isinstance(existing.extra, dict):
                existing.extra = {}
            row = existing
        else:
            row = PanelConnection(
                name=name,
                provider=item.get("provider") or "baota",
            )
            _apply_fields(row, item, _PANEL_CONNECTION_FIELDS)
            if not isinstance(row.extra, dict):
                row.extra = {}
            db.add(row)
        await db.flush()
        if item.get("id") is not None:
            id_map[int(item["id"])] = row.id
    await db.flush()
    return id_map


async def _import_alert_policies(
    db: AsyncSession, items: list[dict[str, Any]], channel_map: dict[int, int]
) -> int:
    count = 0
    for item in items:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        existing = await _find_one(db, AlertPolicy, AlertPolicy.name == name)
        channel_ids = _remap_ids(item.get("channel_ids"), channel_map) or []
        if existing:
            _apply_fields(existing, item, _ALERT_FIELDS)
            existing.channel_ids = channel_ids
        else:
            row = AlertPolicy(
                name=name,
                condition_type=item.get("condition_type") or "traffic_spike",
            )
            _apply_fields(row, item, _ALERT_FIELDS)
            row.channel_ids = channel_ids
            db.add(row)
        count += 1
    await db.flush()
    return count


async def _import_ai_settings(db: AsyncSession, item: dict[str, Any] | None) -> bool:
    if not item:
        return False
    setting = (
        await db.execute(select(AiGuardSetting).where(AiGuardSetting.id == 1))
    ).scalar_one_or_none()
    if setting is None:
        setting = AiGuardSetting(id=1)
        db.add(setting)
        await db.flush()

    for key in (
        "enabled",
        "provider_base_url",
        "model",
        "temperature",
        "max_tokens",
        "chat_enabled",
        "floating_chat_enabled",
        "defense_enabled",
        "default_apply_mode",
        "max_logs_per_analysis",
        "analysis_cooldown_sec",
        "auto_block_min_confidence",
    ):
        if key in item:
            setattr(setting, key, item[key])

    api_key = item.get("api_key")
    if api_key:
        setting.api_key_encrypted = encrypt_secret(str(api_key))
    await db.flush()
    return True


async def _import_ai_policies(
    db: AsyncSession, items: list[dict[str, Any]], channel_map: dict[int, int]
) -> int:
    count = 0
    for item in items:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        existing = await _find_one(db, AiGuardPolicy, AiGuardPolicy.name == name)
        channel_ids = _remap_ids(item.get("channel_ids"), channel_map) or []
        if existing:
            _apply_fields(existing, item, _AI_POLICY_FIELDS)
            existing.channel_ids = channel_ids
            existing.last_triggered_at = None
        else:
            row = AiGuardPolicy(
                name=name,
                trigger_type=item.get("trigger_type") or "manual",
            )
            _apply_fields(row, item, _AI_POLICY_FIELDS)
            row.channel_ids = channel_ids
            db.add(row)
        count += 1
    await db.flush()
    return count


async def _import_waf_settings(db: AsyncSession, item: dict[str, Any] | None) -> bool:
    if not item:
        return False
    waf = (await db.execute(select(WafSetting).where(WafSetting.id == 1))).scalar_one_or_none()
    if waf is None:
        waf = WafSetting(id=1)
        db.add(waf)
        await db.flush()
    for attr in sa_inspect(waf).mapper.column_attrs:
        key = attr.key
        if key in _WAF_SETTING_SKIP or key not in item:
            continue
        setattr(waf, key, item[key])
    await db.flush()
    return True


async def apply_import(
    db: AsyncSession,
    payload: dict[str, Any],
    sections: list[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("备份内容必须是 JSON 对象")
    if payload.get("format") != FORMAT_NAME:
        raise ValueError("不是有效的流盾备份文件（format 不匹配）")
    version = int(payload.get("version") or 0)
    if version < 1 or version > FORMAT_VERSION:
        raise ValueError(f"不支持的备份版本: {version}")

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("备份缺少 data 字段")

    file_sections = _expand_section_aliases(
        list(payload.get("sections") or list(ALL_SECTIONS))
    )
    requested = _normalize_sections(sections or file_sections)
    # only import sections that both requested and present in file sections metadata
    selected = [s for s in requested if s in set(file_sections) or any(
        bag in data for bag in SECTION_DEFS[s]["bags"]
    )]

    summary: dict[str, Any] = {"sections": selected, "counts": {}}
    cert_map: dict[int, int] = {}
    site_map: dict[int, int] = {}
    channel_map: dict[int, int] = {}
    group_map: dict[int, int] = {}

    # Old backups nested IP groups under "rules"; still import them when only rules is selected.
    file_section_set = set(file_sections)
    legacy_ip_groups = (
        "rules" in selected
        and "ip_groups" not in selected
        and "ip_groups" not in file_section_set
        and bool(data.get("ip_groups"))
    )
    import_ip_groups = "ip_groups" in selected or legacy_ip_groups

    # Channels / panel accounts first so certificate notify and push IDs can remap.
    panel_map: dict[int, int] = {}
    if "system_settings" in selected:
        channel_map = await _import_channels(db, data.get("notification_channels") or [])
        summary["counts"]["notification_channels"] = len(channel_map)
        panel_map = await _import_panel_connections(db, data.get("panel_connections") or [])
        summary["counts"]["panel_connections"] = len(panel_map)
    else:
        for row in (await db.execute(select(NotificationChannel))).scalars().all():
            channel_map[row.id] = row.id
        for row in (await db.execute(select(PanelConnection))).scalars().all():
            panel_map[row.id] = row.id

    # Same-instance identity maps when related section is not part of this import.
    if "certificates" not in selected:
        for row in (await db.execute(select(Certificate))).scalars().all():
            cert_map[row.id] = row.id
    if "sites" not in selected:
        for row in (await db.execute(select(Site))).scalars().all():
            site_map[row.id] = row.id
    if not import_ip_groups:
        for row in (await db.execute(select(IpGroup))).scalars().all():
            group_map[row.id] = row.id

    if "certificates" in selected:
        cert_map = await _import_certificates(
            db, data.get("certificates") or [], channel_map, panel_map
        )
        summary["counts"]["certificates"] = len(cert_map)

    if "sites" in selected:
        site_map = await _import_sites(db, data.get("sites") or [], cert_map)
        summary["counts"]["sites"] = len(site_map)

    if import_ip_groups:
        group_map = await _import_ip_groups(db, data.get("ip_groups") or [])
        summary["counts"]["ip_groups"] = len(group_map)

    if "rules" in selected:
        summary["counts"]["rules"] = await _import_named_scoped(
            db,
            model=Rule,
            items=data.get("rules") or [],
            fields=_RULE_FIELDS,
            site_map=site_map,
            group_map=group_map,
        )
        summary["counts"]["blacklist"] = await _import_named_scoped(
            db,
            model=IpList,
            items=data.get("blacklist") or [],
            fields=_IPLIST_FIELDS,
            site_map=site_map,
            group_map=group_map,
            extra={"list_type": "black"},
            name_match_extra=IpList.list_type == "black",
        )
        summary["counts"]["whitelist"] = await _import_named_scoped(
            db,
            model=IpList,
            items=data.get("whitelist") or [],
            fields=_IPLIST_FIELDS,
            site_map=site_map,
            group_map=group_map,
            extra={"list_type": "white"},
            name_match_extra=IpList.list_type == "white",
        )
        summary["counts"]["exceptions"] = await _import_named_scoped(
            db,
            model=Exception_,
            items=data.get("exceptions") or [],
            fields=_EXCEPTION_FIELDS,
            site_map=site_map,
            group_map=group_map,
        )
        summary["counts"]["ratelimits"] = await _import_named_scoped(
            db,
            model=RateLimit,
            items=data.get("ratelimits") or [],
            fields=_RATELIMIT_FIELDS,
            site_map=site_map,
            group_map=group_map,
        )

    if "bots" in selected:
        summary["counts"]["bot_categories"] = await _import_bot_categories(
            db, data.get("bot_categories") or []
        )
        summary["counts"]["bots"] = await _import_bots(
            db, data.get("bots") or [], site_map
        )

    if "system_settings" in selected:
        summary["counts"]["alert_policies"] = await _import_alert_policies(
            db, data.get("alert_policies") or [], channel_map
        )
        summary["counts"]["waf_settings"] = int(
            await _import_waf_settings(db, data.get("waf_settings"))
        )

    if "ai_config" in selected:
        summary["counts"]["ai_guard_settings"] = int(
            await _import_ai_settings(db, data.get("ai_guard_settings"))
        )
    if "ai_policies" in selected:
        summary["counts"]["ai_guard_policies"] = await _import_ai_policies(
            db, data.get("ai_guard_policies") or [], channel_map
        )

    await db.commit()

    reload_ok = True
    try:
        await rule_sync.publish(db)
    except Exception as exc:  # noqa: BLE001
        log.exception("rule_sync after import failed: %s", exc)
        reload_ok = False
        summary["engine_error"] = f"配置已导入，但规则同步失败：{exc}"
        try:
            await get_redis_dirty()
        except Exception:  # noqa: BLE001
            pass

    if "sites" in selected or "certificates" in selected:
        try:
            reload_result = await nginx_conf.regenerate(db)
            reload_ok = bool(reload_result) and reload_ok
            if not reload_result.ok:
                summary["engine_error"] = nginx_conf.format_reload_warn_message(
                    reload_result,
                    saved_label="配置已导入",
                )
        except Exception as exc:  # noqa: BLE001
            log.exception("nginx regenerate after import failed: %s", exc)
            reload_ok = False
            summary["engine_error"] = f"配置已导入，但引擎重载失败：{exc}"

    summary["engine_synced"] = reload_ok
    return summary


async def get_redis_dirty() -> None:
    from app.core.redis import get_redis
    from app.services.rule_sync import DIRTY_KEY

    await get_redis().set(DIRTY_KEY, "1")
