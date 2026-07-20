"""ClickHouse analytics table names and TTL defaults."""

CH_INCIDENTS_TABLE = "ai_guard_incidents"
CH_ALERT_LOGS_TABLE = "alert_notification_logs"
CH_TRAFFIC_ALERTS_TABLE = "traffic_alerts"

INCIDENT_TTL_DAYS = 180
ALERT_LOG_TTL_DAYS = 90
TRAFFIC_ALERT_TTL_DAYS = 90

REDIS_SEQ_INCIDENT = "waf:seq:incident_id"
REDIS_SEQ_ALERT_LOG = "waf:seq:alert_log_id"
REDIS_SEQ_TRAFFIC_ALERT = "waf:seq:traffic_alert_id"
