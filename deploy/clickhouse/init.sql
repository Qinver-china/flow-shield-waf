-- ClickHouse schema for WAF logs
CREATE DATABASE IF NOT EXISTS waf;

CREATE TABLE IF NOT EXISTS waf.waf_logs (
  ts DateTime64(3),
  site_id Nullable(UInt32),
  domain LowCardinality(String),
  client_ip String,
  ip_is_private UInt8 DEFAULT 0,
  xff_first Nullable(String),
  geo_country LowCardinality(Nullable(String)),
  geo_region LowCardinality(Nullable(String)),
  geo_city LowCardinality(Nullable(String)),
  geo_isp LowCardinality(Nullable(String)),
  geo_asn Nullable(UInt32),
  method LowCardinality(String),
  scheme LowCardinality(String),
  http_version LowCardinality(String),
  request_uri String,
  uri_path String,
  uri_ext LowCardinality(String),
  uri_depth UInt8 DEFAULT 0,
  uri_pattern String DEFAULT '',
  uri_query String DEFAULT '',
  query_count UInt16 DEFAULT 0,
  referer String DEFAULT '',
  referer_host LowCardinality(Nullable(String)),
  ua String,
  bot_name LowCardinality(Nullable(String)),
  bot_category LowCardinality(Nullable(String)),
  ua_family LowCardinality(Nullable(String)),
  ua_os LowCardinality(Nullable(String)),
  ua_browser LowCardinality(Nullable(String)),
  tls_version LowCardinality(Nullable(String)),
  tls_cipher LowCardinality(Nullable(String)),
  tls_ja3 Nullable(String),
  rule_id Nullable(UInt32),
  rule_name LowCardinality(Nullable(String)),
  source LowCardinality(String),
  mode LowCardinality(String),
  action LowCardinality(String),
  blocked UInt8 DEFAULT 0,
  log_type LowCardinality(String),
  request_id String,
  evaluated String DEFAULT '{}',
  payload String DEFAULT '{}'
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (site_id, ts, client_ip, uri_path)
TTL toDateTime(ts) + INTERVAL 30 DAY
SETTINGS index_granularity = 8192, allow_nullable_key = 1;

CREATE TABLE IF NOT EXISTS waf.mv_stats_core_hourly (
  hour DateTime,
  site_id Nullable(UInt32),
  rule_id Nullable(UInt32),
  source LowCardinality(String),
  mode LowCardinality(String),
  blocked UInt8,
  log_type LowCardinality(String),
  cnt UInt64
)
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, site_id, rule_id, source, mode, blocked, log_type)
SETTINGS allow_nullable_key = 1;

CREATE MATERIALIZED VIEW IF NOT EXISTS waf.mv_stats_core_hourly_mv
TO waf.mv_stats_core_hourly AS
SELECT
  toStartOfHour(ts) AS hour,
  site_id,
  rule_id,
  source,
  mode,
  blocked,
  log_type,
  count() AS cnt
FROM waf.waf_logs
GROUP BY hour, site_id, rule_id, source, mode, blocked, log_type;

CREATE TABLE IF NOT EXISTS waf.traffic_minute (
  minute DateTime,
  requests UInt64,
  site_id Nullable(UInt32)
)
ENGINE = SummingMergeTree
ORDER BY (minute, site_id)
TTL minute + INTERVAL 90 DAY
SETTINGS allow_nullable_key = 1;

CREATE TABLE IF NOT EXISTS waf.traffic_window_snapshot (
  ts DateTime,
  site_id Nullable(UInt32),
  window_sec UInt32,
  requests UInt64,
  qps Float64
)
ENGINE = MergeTree
ORDER BY (site_id, window_sec, ts)
TTL ts + INTERVAL 90 DAY
SETTINGS allow_nullable_key = 1;

CREATE TABLE IF NOT EXISTS waf.ai_guard_incidents (
  incident_id UInt64,
  version UInt64,
  policy_id Nullable(UInt32),
  site_id Nullable(UInt32),
  status LowCardinality(String),
  trigger_snapshot String DEFAULT '{}',
  log_sample_meta String DEFAULT '{}',
  analysis_report String DEFAULT '{}',
  suggested_rule String DEFAULT '{}',
  applied_rule_id Nullable(UInt32),
  apply_mode Nullable(String),
  error_detail Nullable(String),
  notification_log String DEFAULT '[]',
  created_at DateTime64(3),
  updated_at DateTime64(3)
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (incident_id)
TTL toDateTime(updated_at) + INTERVAL 180 DAY
SETTINGS allow_nullable_key = 1;

CREATE TABLE IF NOT EXISTS waf.alert_notification_logs (
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
TTL toDateTime(created_at) + INTERVAL 90 DAY;

CREATE TABLE IF NOT EXISTS waf.traffic_alerts (
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
TTL toDateTime(detected_at) + INTERVAL 90 DAY
SETTINGS allow_nullable_key = 1;
