"""Catalog of alert policy condition types for admin notifications."""

from app.constants.alert_site_scope import SITE_SCOPE_OPTIONS
from app.constants.system_metrics import system_metric_window_options
from app.constants.traffic_windows import traffic_window_options

TRAFFIC_WINDOWS = traffic_window_options()
SYSTEM_WINDOWS = system_metric_window_options()

BLOCK_WINDOWS_MIN = [
    {"value": 5, "label": "5 分钟"},
    {"value": 15, "label": "15 分钟"},
    {"value": 30, "label": "30 分钟"},
    {"value": 60, "label": "60 分钟"},
]

_SITE_PARAM = {
    "key": "site_scope",
    "label": "生效站点",
    "kind": "alert_site_scope",
    "required": False,
    "options": SITE_SCOPE_OPTIONS,
}

_SYSTEM_WINDOW_PARAM = {
    "key": "window_sec",
    "label": "统计窗口",
    "kind": "system_window",
    "required": True,
}

ALERT_CONDITION_TYPES: list[dict] = [
    {
        "type": "traffic.baseline_gt",
        "label": "流量高于基线",
        "category": "流量异常",
        "description": "检测突发流量、CC 攻击。对比同星期同时段历史基线；部署后数小时可显示初步基线，运行数天后更准确。",
        "params": [
            _SITE_PARAM,
            {"key": "window_sec", "label": "时间窗口", "kind": "traffic_window", "required": True},
            {"key": "percent", "label": "高于基线 (%)", "kind": "number", "min": 1, "required": True},
        ],
    },
    {
        "type": "traffic.baseline_lt",
        "label": "流量低于基线",
        "category": "流量异常",
        "description": "检测流量异常下跌（源站故障、DNS 问题、线路中断等）。",
        "params": [
            _SITE_PARAM,
            {"key": "window_sec", "label": "时间窗口", "kind": "traffic_window", "required": True},
            {"key": "percent", "label": "低于基线 (%)", "kind": "number", "min": 1, "required": True},
        ],
    },
    {
        "type": "traffic.abs_gt",
        "label": "请求量高于固定值",
        "category": "流量异常",
        "description": "不依赖基线，适合新站或固定容量上限告警。",
        "params": [
            _SITE_PARAM,
            {"key": "window_sec", "label": "时间窗口", "kind": "traffic_window", "required": True},
            {"key": "threshold", "label": "请求量上限", "kind": "number", "min": 1, "required": True},
        ],
    },
    {
        "type": "traffic.abs_lt",
        "label": "请求量低于固定值",
        "category": "流量异常",
        "description": "长时间几乎无流量时提醒（可能 WAF/站点不可用）。",
        "params": [
            _SITE_PARAM,
            {"key": "window_sec", "label": "时间窗口", "kind": "traffic_window", "required": True},
            {"key": "threshold", "label": "请求量下限", "kind": "number", "min": 0, "required": True},
        ],
    },
    {
        "type": "traffic.qps_gt",
        "label": "QPS 高于固定值",
        "category": "流量异常",
        "description": "按所选时间窗口内的平均 QPS（请求量 ÷ 窗口秒数）判断。",
        "params": [
            _SITE_PARAM,
            {"key": "window_sec", "label": "时间窗口", "kind": "traffic_window", "required": True},
            {"key": "threshold", "label": "QPS 上限", "kind": "number", "min": 0, "required": True},
        ],
    },
    {
        "type": "traffic.qps_lt",
        "label": "QPS 低于固定值",
        "category": "流量异常",
        "description": "检测平均 QPS 异常偏低。",
        "params": [
            _SITE_PARAM,
            {"key": "window_sec", "label": "时间窗口", "kind": "traffic_window", "required": True},
            {"key": "threshold", "label": "QPS 下限", "kind": "number", "min": 0, "required": True},
        ],
    },
    {
        "type": "traffic.origin_abs_gt",
        "label": "回源请求量高于固定值",
        "category": "流量异常",
        "description": "统计 WAF 放行后实际回源的请求量（不含拦截）。",
        "params": [
            _SITE_PARAM,
            {"key": "window_sec", "label": "时间窗口", "kind": "traffic_window", "required": True},
            {"key": "threshold", "label": "回源请求量上限", "kind": "number", "min": 1, "required": True},
        ],
    },
    {
        "type": "traffic.origin_abs_lt",
        "label": "回源请求量低于固定值",
        "category": "流量异常",
        "description": "回源流量异常偏低时提醒（可能源站故障或大量请求被拦截）。",
        "params": [
            _SITE_PARAM,
            {"key": "window_sec", "label": "时间窗口", "kind": "traffic_window", "required": True},
            {"key": "threshold", "label": "回源请求量下限", "kind": "number", "min": 0, "required": True},
        ],
    },
    {
        "type": "traffic.origin_qps_gt",
        "label": "回源 QPS 高于固定值",
        "category": "流量异常",
        "description": "按所选时间窗口内的平均回源 QPS（回源请求量 ÷ 窗口秒数）判断。",
        "params": [
            _SITE_PARAM,
            {"key": "window_sec", "label": "时间窗口", "kind": "traffic_window", "required": True},
            {"key": "threshold", "label": "回源 QPS 上限", "kind": "number", "min": 0, "required": True},
        ],
    },
    {
        "type": "traffic.origin_qps_lt",
        "label": "回源 QPS 低于固定值",
        "category": "流量异常",
        "description": "检测平均回源 QPS 异常偏低。",
        "params": [
            _SITE_PARAM,
            {"key": "window_sec", "label": "时间窗口", "kind": "traffic_window", "required": True},
            {"key": "threshold", "label": "回源 QPS 下限", "kind": "number", "min": 0, "required": True},
        ],
    },
    {
        "type": "traffic.burst_logging",
        "label": "流量自动取证已触发",
        "category": "流量异常",
        "description": "日志设置为「按流量自动启停」且已超过阈值进入取证模式时通知。",
        "params": [],
    },
    {
        "type": "security.block_count",
        "label": "拦截次数超过阈值",
        "category": "安全事件",
        "description": "短时间内大量拦截，可能有扫描、爆破或 Web 攻击。",
        "params": [
            _SITE_PARAM,
            {"key": "window_min", "label": "统计窗口", "kind": "block_window", "required": True},
            {"key": "threshold", "label": "拦截次数", "kind": "number", "min": 1, "required": True},
        ],
    },
    {
        "type": "security.block_rate",
        "label": "拦截率超过阈值",
        "category": "安全事件",
        "description": "拦截占比过高，攻击流量可能已占主导。",
        "params": [
            _SITE_PARAM,
            {"key": "window_min", "label": "统计窗口", "kind": "block_window", "required": True},
            {"key": "percent", "label": "拦截率 (%)", "kind": "number", "min": 1, "max": 100, "required": True},
        ],
    },
    {
        "type": "system.container_cpu_gt",
        "label": "容器 CPU 占用过高",
        "category": "系统 CPU",
        "description": "按窗口平均容器 CPU 占用率（cgroup 换算）判断，适合节点过载时告警。",
        "params": [
            _SYSTEM_WINDOW_PARAM,
            {"key": "threshold", "label": "CPU 占用 (%)", "kind": "number", "min": 0, "max": 1000, "required": True},
        ],
    },
    {
        "type": "system.host_cpu_gt",
        "label": "宿主机 CPU 占用过高",
        "category": "系统 CPU",
        "description": "按窗口平均宿主机 CPU 占用率判断（/proc/stat）。",
        "params": [
            _SYSTEM_WINDOW_PARAM,
            {"key": "threshold", "label": "CPU 占用 (%)", "kind": "number", "min": 0, "max": 100, "required": True},
        ],
    },
]

CONDITION_TYPE_MAP = {c["type"]: c for c in ALERT_CONDITION_TYPES}

CHANNEL_TYPES = [
    {"value": "email", "label": "邮件通知", "implemented": True},
    {"value": "sms", "label": "短信通知", "implemented": False},
    {"value": "webhook", "label": "Webhook", "implemented": False},
    {"value": "dingtalk", "label": "钉钉机器人", "implemented": False},
]
