"""Display-related global settings."""

DEFAULT_TIMEZONE = "Asia/Shanghai"

TIMEZONE_OPTIONS: list[dict[str, str]] = [
    {"value": "Asia/Shanghai", "label": "中国标准时间（上海，UTC+8）"},
    {"value": "Asia/Hong_Kong", "label": "香港时间（UTC+8）"},
    {"value": "Asia/Taipei", "label": "台北时间（UTC+8）"},
    {"value": "Asia/Tokyo", "label": "日本标准时间（UTC+9）"},
    {"value": "Asia/Singapore", "label": "新加坡时间（UTC+8）"},
    {"value": "UTC", "label": "协调世界时（UTC）"},
    {"value": "Europe/London", "label": "伦敦时间"},
    {"value": "America/New_York", "label": "美国东部时间"},
    {"value": "America/Los_Angeles", "label": "美国太平洋时间"},
]

ALLOWED_TIMEZONES = {opt["value"] for opt in TIMEZONE_OPTIONS}
