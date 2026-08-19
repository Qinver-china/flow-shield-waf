/**
 * Log stats / filter dimension layout.
 * Category names align with backend `app/fields/catalog.py` CATEGORY_ORDER.
 * Log-only dimensions live under「防护命中」.
 */

export interface LogStatsDimensionItem {
  key: string;
  label: string;
  /** Brief tooltip when the label alone is ambiguous. */
  desc?: string;
}

export interface LogStatsDimensionGroup {
  label: string;
  items: LogStatsDimensionItem[];
}

/** Prepended in log UI; no rule-field equivalent. */
export const LOG_HIT_CATEGORY = "防护命中";

/** Mirrors `CATEGORY_ORDER` in backend field catalog (after 防护命中). */
export const RULE_FIELD_CATEGORY_ORDER = [
  "网络与地理",
  "URL 与路径",
  "HTTP 请求",
  "客户端识别",
  "时间与流量",
] as const;

export const logStatsDimensionLayout = [
  {
    label: LOG_HIT_CATEGORY,
    items: [
      { key: "rule_id", label: "命中规则", desc: "按规则聚合统计" },
      { key: "source", label: "防护来源", desc: "规则、黑名单、限速等" },
      { key: "mode", label: "防护方式" },
      { key: "blocked", label: "拦截结果" },
      { key: "log_type", label: "日志类型", desc: "防护、访问控制或审计" },
      { key: "site_id", label: "站点" },
    ],
  },
  {
    label: "网络与地理",
    items: [
      { key: "client_ip", label: "客户端 IP" },
      { key: "tcp_ip", label: "直连 IP", desc: "TCP 连接对端 IP" },
      { key: "ip_is_private", label: "IP 是否内网", desc: "是否为内网地址" },
      { key: "scheme", label: "协议" },
      { key: "http_version", label: "HTTP 版本" },
      { key: "geo_country", label: "IP 国家/地区" },
      { key: "geo_region", label: "IP 省/州" },
      { key: "geo_city", label: "IP 城市" },
      { key: "geo_asn", label: "IP ASN", desc: "自治系统编号" },
      { key: "geo_isp", label: "运营商 ISP" },
      { key: "xff_first", label: "X-Forwarded-For", desc: "XFF 首跳 IP" },
    ],
  },
  {
    label: "URL 与路径",
    items: [
      { key: "domain", label: "请求域名" },
      { key: "full_url", label: "完整 URL", desc: "含协议、域名、路径与参数" },
      { key: "request_uri", label: "原始请求行", desc: "请求行中的路径与查询串" },
      { key: "uri_path", label: "请求路径" },
      { key: "uri_ext", label: "文件后缀" },
      { key: "uri_depth", label: "路径深度", desc: "路径层级数" },
      { key: "uri_pattern", label: "路径模式", desc: "归一化后的路径模式" },
      { key: "uri_query", label: "原始查询串", desc: "问号后的原始查询串" },
      { key: "query_count_bucket", label: "查询参数个数", desc: "查询参数数量区间" },
    ],
  },
  {
    label: "HTTP 请求",
    items: [
      { key: "method", label: "请求方法" },
      { key: "referer_host", label: "Referer", desc: "Referer 中的主机名" },
      { key: "ua", label: "User-Agent" },
      { key: "cookie_name", label: "Cookie 参数名", desc: "按 Cookie 键名筛选" },
      { key: "cookie_count_bucket", label: "Cookie 个数", desc: "Cookie 数量区间" },
    ],
  },
  {
    label: "客户端识别",
    items: [
      { key: "bot_name", label: "Bot 名称" },
      { key: "bot_category", label: "Bot 分类" },
      { key: "ua_family", label: "UA 类型", desc: "浏览器或 Bot" },
      { key: "ua_os", label: "操作系统" },
      { key: "ua_browser", label: "浏览器" },
      { key: "tls_version", label: "TLS 版本" },
      { key: "tls_ja3", label: "JA3 指纹", desc: "TLS 客户端指纹" },
    ],
  },
  {
    label: "时间与流量",
    items: [
      { key: "hour_of_day", label: "当前小时" },
      { key: "weekday", label: "星期几" },
    ],
  },
] as const satisfies readonly LogStatsDimensionGroup[];
