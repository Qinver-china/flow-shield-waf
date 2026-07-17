"""End-to-end automated defense pipeline."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_guard import AiGuardIncident, AiGuardPolicy
from app.services.ai_guard.config import AiGuardRuntimeConfig, load_runtime_config
from app.services.ai_guard.defense.applier import apply_rule_draft, check_rule_conflicts
from app.services.ai_guard.defense.rule_generator import analyze_and_suggest
from app.services.ai_guard.ports import log_sampler, notifier

log = logging.getLogger("waf.ai_guard.pipeline")


async def run_defense_for_policy(
    db: AsyncSession,
    policy: AiGuardPolicy,
    *,
    trigger_snapshot: dict,
    site_id: int | None = None,
) -> AiGuardIncident:
    cfg = await load_runtime_config(db)
    if not cfg.enabled or not cfg.defense_enabled or not cfg.api_key:
        raise ValueError("AI 防护未启用或未配置 API Key")

    apply_mode = policy.apply_mode or cfg.default_apply_mode
    window_min = int(policy.trigger_params.get("window_min") or trigger_snapshot.get("window_min") or 5)

    policy.last_triggered_at = datetime.utcnow()
    await db.commit()

    incident = AiGuardIncident(
        policy_id=policy.id,
        site_id=site_id,
        status="analyzing",
        trigger_snapshot=trigger_snapshot,
        apply_mode=apply_mode,
        notification_log=[],
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    notify_on = policy.notify_on or ["trigger", "result"]
    channel_ids = policy.channel_ids or []

    if "trigger" in notify_on:
        entries = await notifier.notify_policy(
            db,
            channel_ids=channel_ids,
            subject=f"流盾 AI 防护：{policy.name}",
            body=f"触发条件已命中，开始分析近 {window_min} 分钟日志。\n\n快照：{trigger_snapshot}",
        )
        incident.notification_log = (incident.notification_log or []) + entries
        await db.commit()

    try:
        rows, meta = await log_sampler.sample(
            window_min=window_min,
            site_id=site_id,
            max_rows=cfg.max_logs_per_analysis,
        )
        incident.log_sample_meta = meta

        if "analyzing" in notify_on:
            entries = await notifier.notify_policy(
                db,
                channel_ids=channel_ids,
                subject=f"流盾 AI 防护：分析中",
                body=f"已取样 {meta.get('sampled', 0)} 条日志（拦截 {meta.get('blocked_count', 0)} 条）",
            )
            incident.notification_log = (incident.notification_log or []) + entries
            await db.commit()

        analysis = await analyze_and_suggest(
            db, cfg, log_rows=rows, log_meta=meta, site_id=site_id
        )
        report = analysis.model_dump()
        report["blocked_ratio"] = meta.get("blocked_count", 0) / max(meta.get("sampled", 1), 1)
        incident.analysis_report = report
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

        if "result" in notify_on:
            body = (
                f"分析完成：{analysis.summary}\n\n"
                f"置信度：{analysis.confidence:.0%}\n"
                f"建议规则：{incident.suggested_rule.get('name')}\n"
                f"应用模式：{apply_mode}"
                + (f"\n已创建规则 #{rule_id}（{effective_mode}）" if rule_id else "\n待管理员审核后应用")
            )
            entries = await notifier.notify_policy(
                db,
                channel_ids=channel_ids,
                subject=f"流盾 AI 防护：分析结果",
                body=body,
            )
            incident.notification_log = (incident.notification_log or []) + entries

        await db.commit()
        await db.refresh(incident)
        return incident

    except Exception as exc:  # noqa: BLE001
        log.exception("ai guard defense pipeline failed policy=%s", policy.id)
        incident.status = "failed"
        incident.error_detail = str(exc)
        await db.commit()
        await db.refresh(incident)
        raise


async def apply_incident_rule(
    db: AsyncSession,
    incident_id: int,
    *,
    apply_mode: str | None = None,
) -> AiGuardIncident:
    incident = await db.get(AiGuardIncident, incident_id)
    if incident is None:
        raise ValueError("事件不存在")
    if not incident.suggested_rule:
        raise ValueError("没有可应用的规则建议")
    if incident.applied_rule_id:
        raise ValueError("规则已应用")

    cfg = await load_runtime_config(db)
    mode = apply_mode or incident.apply_mode or cfg.default_apply_mode
    rule_id, _ = await apply_rule_draft(
        db,
        incident.suggested_rule,
        apply_mode=mode,
        config=cfg,
        analysis=incident.analysis_report,
    )
    incident.applied_rule_id = rule_id
    incident.status = "applied"
    incident.apply_mode = mode
    await db.commit()
    await db.refresh(incident)
    return incident


async def rollback_incident(db: AsyncSession, incident_id: int) -> AiGuardIncident:
    from app.services.ai_guard.ports import writer

    incident = await db.get(AiGuardIncident, incident_id)
    if incident is None:
        raise ValueError("事件不存在")
    if not incident.applied_rule_id:
        raise ValueError("没有已应用的规则可回滚")
    await writer.delete_rule(db, incident.applied_rule_id)
    incident.applied_rule_id = None
    incident.status = "suggested"
    await db.commit()
    await db.refresh(incident)
    return incident
