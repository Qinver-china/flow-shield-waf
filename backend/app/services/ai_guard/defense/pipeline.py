"""End-to-end automated defense pipeline."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_guard import AiGuardPolicy
from app.services.ai_guard.config import AiGuardRuntimeConfig, load_runtime_config
from app.services.ai_guard.defense.applier import apply_rule_draft, check_rule_conflicts
from app.services.ai_guard.defense.rule_generator import analyze_and_suggest
from app.services.ai_guard.mode_guide import normalize_apply_mode
from app.services.ai_guard.ports import (
    DEFENSE_INITIAL_MAX_ROWS,
    DEFENSE_INITIAL_WINDOW_MIN,
    log_sampler,
    notifier,
)
from app.services.analytics.incident_store import IncidentRecord, IncidentStore

log = logging.getLogger("waf.ai_guard.pipeline")

_incidents = IncidentStore()


async def run_defense_for_policy(
    db: AsyncSession,
    policy: AiGuardPolicy,
    *,
    trigger_snapshot: dict,
    site_id: int | None = None,
) -> IncidentRecord:
    cfg = await load_runtime_config(db)
    if not cfg.enabled or not cfg.defense_enabled or not cfg.api_key:
        raise ValueError("AI 防护未启用或未配置 API Key")

    apply_mode = normalize_apply_mode(policy.apply_mode or cfg.default_apply_mode)
    window_min = int(policy.trigger_params.get("window_min") or trigger_snapshot.get("window_min") or 5)

    policy.last_triggered_at = datetime.utcnow()
    await db.commit()

    incident = await _incidents.create(
        policy_id=policy.id,
        site_id=site_id,
        status="analyzing",
        trigger_snapshot=trigger_snapshot,
        apply_mode=apply_mode,
        notification_log=[],
    )

    notify_on = policy.notify_on or ["trigger", "result"]
    channel_ids = policy.channel_ids or []

    if "trigger" in notify_on:
        from app.services.ai_guard.defense.traffic_context import build_defense_traffic_overview
        from app.services.ai_guard.incident_email import build_trigger_email

        focus_window_sec = trigger_snapshot.get("window_sec")
        try:
            focus_window_sec = int(focus_window_sec) if focus_window_sec not in (None, "") else None
        except (TypeError, ValueError):
            focus_window_sec = None
        try:
            traffic_overview = await build_defense_traffic_overview(
                db,
                focus_site_id=site_id,
                focus_window_sec=focus_window_sec,
                log_window_min=max(window_min, DEFENSE_INITIAL_WINDOW_MIN),
            )
        except Exception:  # noqa: BLE001
            log.exception("ai guard trigger email traffic overview failed policy=%s", policy.id)
            traffic_overview = None

        try:
            from app.services.system_metrics import read_system_metrics_snapshot

            system_metrics = await read_system_metrics_snapshot()
        except Exception:  # noqa: BLE001
            log.exception("ai guard trigger email system metrics failed policy=%s", policy.id)
            system_metrics = None

        plain, html_body = build_trigger_email(
            policy_name=policy.name,
            window_min=window_min,
            trigger_snapshot=trigger_snapshot,
            traffic_overview=traffic_overview,
            system_metrics=system_metrics,
        )
        entries = await notifier.notify_policy(
            db,
            channel_ids=channel_ids,
            subject=f"流盾 AI 防护：{policy.name}",
            body=plain,
            html_body=html_body,
        )
        incident.notification_log = (incident.notification_log or []) + entries
        incident = await _incidents.upsert(incident)

    try:
        rows, meta = await log_sampler.sample(
            window_min=DEFENSE_INITIAL_WINDOW_MIN,
            site_id=site_id,
            max_rows=min(cfg.max_logs_per_analysis, DEFENSE_INITIAL_MAX_ROWS),
            passed_only=True,
        )
        incident.log_sample_meta = meta

        if "analyzing" in notify_on:
            from app.services.ai_guard.incident_email import build_analyzing_email

            plain, html_body = build_analyzing_email(
                policy_name=policy.name,
                sampled=int(meta.get("sampled", 0)),
                blocked_count=int(meta.get("blocked_count", 0)),
            )
            entries = await notifier.notify_policy(
                db,
                channel_ids=channel_ids,
                subject="流盾 AI 防护：分析中",
                body=plain,
                html_body=html_body,
            )
            incident.notification_log = (incident.notification_log or []) + entries
            incident = await _incidents.upsert(incident)

        analysis = await analyze_and_suggest(
            db,
            cfg,
            log_rows=rows,
            log_meta=meta,
            site_id=site_id,
            custom_prompt=policy.custom_prompt,
            trigger_snapshot=trigger_snapshot,
        )
        report = analysis.model_dump()
        try:
            win_stats = await log_sampler.window_block_stats(
                window_min=DEFENSE_INITIAL_WINDOW_MIN,
                site_id=site_id,
            )
            report["blocked_ratio"] = float(win_stats["blocked_ratio"])
            report["window_request_count"] = int(win_stats["total"])
            report["window_blocked_count"] = int(win_stats["blocked"])
        except Exception:  # noqa: BLE001
            log.exception("ai guard window block stats failed policy=%s", policy.id)
            report["blocked_ratio"] = 0.0
        incident.analysis_report = report

        rule_id = None
        if analysis.create_rule and analysis.suggested_rule:
            incident.suggested_rule = analysis.suggested_rule.model_dump()
            conflicts = await check_rule_conflicts(db, incident.suggested_rule)
            if conflicts:
                report["conflict_warnings"] = conflicts
                incident.analysis_report = report

            rule_id = None
            effective_mode = apply_mode
            try:
                rule_id, effective_mode = await apply_rule_draft(
                    db,
                    incident.suggested_rule,
                    apply_mode=apply_mode,
                    config=cfg,
                    analysis=report,
                )
            except ValueError as exc:
                report["apply_error"] = str(exc)
                incident.analysis_report = report
                log.warning("ai guard rule apply validation failed: %s", exc)

            if rule_id:
                incident.applied_rule_id = rule_id
                incident.status = "applied"
            else:
                incident.status = "suggested"
        else:
            incident.suggested_rule = None
            incident.status = "analyzed"

        if "result" in notify_on:
            from app.services.ai_guard.incident_email import build_analysis_result_email
            from app.services import waf_settings

            panel_url = await waf_settings.get_panel_public_url(db)
            plain, html_body = build_analysis_result_email(
                incident_id=incident.incident_id,
                policy_name=policy.name,
                panel_public_url=panel_url,
                analysis_report=incident.analysis_report,
                suggested_rule=incident.suggested_rule,
                status=incident.status,
                applied_rule_id=incident.applied_rule_id,
                apply_mode=apply_mode if rule_id else incident.apply_mode,
                error_detail=report.get("apply_error"),
            )
            entries = await notifier.notify_policy(
                db,
                channel_ids=channel_ids,
                subject=f"流盾 AI 防护：分析结果 · {policy.name}",
                body=plain,
                html_body=html_body,
            )
            incident.notification_log = (incident.notification_log or []) + entries

        incident = await _incidents.upsert(incident)
        return incident

    except Exception as exc:  # noqa: BLE001
        log.exception("ai guard defense pipeline failed policy=%s", policy.id)
        incident.status = "failed"
        incident.error_detail = str(exc)
        if "result" in notify_on:
            from app.services.ai_guard.incident_email import build_analysis_result_email
            from app.services import waf_settings

            panel_url = await waf_settings.get_panel_public_url(db)
            plain, html_body = build_analysis_result_email(
                incident_id=incident.incident_id,
                policy_name=policy.name,
                panel_public_url=panel_url,
                analysis_report=incident.analysis_report,
                suggested_rule=incident.suggested_rule,
                status="failed",
                error_detail=str(exc),
            )
            try:
                entries = await notifier.notify_policy(
                    db,
                    channel_ids=channel_ids,
                    subject=f"流盾 AI 防护：分析失败 · {policy.name}",
                    body=plain,
                    html_body=html_body,
                )
                incident.notification_log = (incident.notification_log or []) + entries
            except Exception:  # noqa: BLE001
                log.exception("ai guard failure notify failed policy=%s", policy.id)
        incident = await _incidents.upsert(incident)
        raise


async def apply_incident_rule(
    db: AsyncSession,
    incident_id: int,
    *,
    apply_mode: str | None = None,
) -> IncidentRecord:
    incident = await _incidents.get(incident_id)
    if incident is None:
        raise ValueError("事件不存在")
    if not incident.suggested_rule:
        raise ValueError("没有可应用的规则建议")
    if incident.applied_rule_id:
        raise ValueError("规则已应用")

    cfg = await load_runtime_config(db)
    mode = apply_mode or incident.apply_mode or cfg.default_apply_mode
    # 面板/邮件「应用」必须真正建规则；suggest_only 仅约束自动流水线。
    if mode == "suggest_only":
        mode = "auto_handle"
    rule_id, effective_mode = await apply_rule_draft(
        db,
        incident.suggested_rule,
        apply_mode=mode,
        config=cfg,
        analysis=incident.analysis_report,
    )
    if not rule_id:
        raise ValueError("规则未能创建")
    incident.applied_rule_id = rule_id
    incident.status = "applied"
    incident.apply_mode = effective_mode
    return await _incidents.upsert(incident)


async def rollback_incident(db: AsyncSession, incident_id: int) -> IncidentRecord:
    from app.services.ai_guard.ports import writer

    incident = await _incidents.get(incident_id)
    if incident is None:
        raise ValueError("事件不存在")
    if not incident.applied_rule_id:
        raise ValueError("没有已应用的规则可回滚")
    await writer.delete_rule(db, incident.applied_rule_id)
    incident.applied_rule_id = None
    incident.status = "suggested"
    return await _incidents.upsert(incident)


async def dismiss_incident(incident_id: int) -> IncidentRecord:
    incident = await _incidents.get(incident_id)
    if incident is None:
        raise ValueError("事件不存在")
    incident.status = "dismissed"
    return await _incidents.upsert(incident)


STALE_SUGGESTED_HOURS = 24


async def expire_stale_suggested_incidents(
    *,
    max_age_hours: int = STALE_SUGGESTED_HOURS,
    limit: int = 200,
) -> int:
    """Auto-dismiss suggested incidents left without manual action for too long."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(hours=max_age_hours)
    stale = await _incidents.list_stale(
        statuses=["suggested"],
        before=cutoff,
        limit=limit,
    )
    if not stale:
        return 0

    dismissed = 0
    now_iso = now.isoformat(timespec="seconds") + "Z"
    for incident in stale:
        if incident.status != "suggested":
            continue
        notes = list(incident.notification_log or [])
        notes.append({
            "event": "auto_dismissed",
            "reason": f"stale_over_{max_age_hours}h",
            "at": now_iso,
        })
        incident.notification_log = notes
        incident.status = "dismissed"
        await _incidents.upsert(incident)
        dismissed += 1

    if dismissed:
        log.info(
            "auto-dismissed %s stale suggested incident(s) older than %sh",
            dismissed,
            max_age_hours,
        )
    return dismissed

