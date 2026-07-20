"""ClickHouse DDL for analytics / event tables."""
from __future__ import annotations

import logging

from app.core.clickhouse import get_clickhouse
from app.services.analytics.constants import (
    ALERT_LOG_TTL_DAYS,
    CH_ALERT_LOGS_TABLE,
    CH_INCIDENTS_TABLE,
    CH_TRAFFIC_ALERTS_TABLE,
    INCIDENT_TTL_DAYS,
    TRAFFIC_ALERT_TTL_DAYS,
)

log = logging.getLogger("waf.analytics.schema")


def ensure_analytics_schema() -> None:
    client = get_clickhouse()
    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {CH_INCIDENTS_TABLE} (
          incident_id UInt64,
          version UInt64,
          policy_id Nullable(UInt32),
          site_id Nullable(UInt32),
          status LowCardinality(String),
          trigger_snapshot String DEFAULT '{{}}',
          log_sample_meta String DEFAULT '{{}}',
          analysis_report String DEFAULT '{{}}',
          suggested_rule String DEFAULT '{{}}',
          applied_rule_id Nullable(UInt32),
          apply_mode Nullable(String),
          error_detail Nullable(String),
          notification_log String DEFAULT '[]',
          created_at DateTime64(3),
          updated_at DateTime64(3)
        )
        ENGINE = ReplacingMergeTree(version)
        ORDER BY (incident_id)
        TTL toDateTime(updated_at) + INTERVAL {INCIDENT_TTL_DAYS} DAY
        SETTINGS allow_nullable_key = 1
        """
    )
    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {CH_ALERT_LOGS_TABLE} (
          id UInt64,
          policy_id UInt32,
          channel_id UInt32,
          status LowCardinality(String),
          message String,
          detail Nullable(String),
          created_at DateTime64(3)
        )
        ENGINE = MergeTree
        ORDER BY (created_at, id)
        TTL toDateTime(created_at) + INTERVAL {ALERT_LOG_TTL_DAYS} DAY
        """
    )
    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {CH_TRAFFIC_ALERTS_TABLE} (
          id UInt64,
          site_id Nullable(UInt32),
          window_sec UInt32,
          current_requests UInt32,
          baseline_avg Float64,
          deviation_ratio Float64,
          severity LowCardinality(String),
          status LowCardinality(String),
          message String,
          detected_at DateTime64(3),
          created_at DateTime64(3)
        )
        ENGINE = MergeTree
        ORDER BY (detected_at, id)
        TTL toDateTime(detected_at) + INTERVAL {TRAFFIC_ALERT_TTL_DAYS} DAY
        SETTINGS allow_nullable_key = 1
        """
    )
    log.info(
        "clickhouse analytics tables ensured: %s, %s, %s",
        CH_INCIDENTS_TABLE,
        CH_ALERT_LOGS_TABLE,
        CH_TRAFFIC_ALERTS_TABLE,
    )
