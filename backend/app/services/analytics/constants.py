"""ClickHouse analytics table names and TTL defaults."""

CH_INCIDENTS_TABLE = "ai_guard_incidents"
CH_ALERT_LOGS_TABLE = "alert_notification_logs"

INCIDENT_TTL_DAYS = 180
ALERT_LOG_TTL_DAYS = 90

REDIS_SEQ_INCIDENT = "waf:seq:incident_id"
REDIS_SEQ_ALERT_LOG = "waf:seq:alert_log_id"
