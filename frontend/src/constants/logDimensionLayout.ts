/**
 * Log stats / filter dimension layout.
 * Category names align with backend `app/fields/catalog.py` CATEGORY_ORDER.
 * Log-only dimensions live under「防护命中」.
 */

export interface LogStatsDimensionItem {
  key: string;
  label: string;
  desc: string;
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
      { key: "rule_id", label: "命中规则", desc: "按规则聚合" },
      { key: "source", label: "防护来源", desc: "规则 / 黑名单 / 限速等" },
      { key: "mode", label: "防护方式", desc: "观察 / 拦截 / 人机验证等" },
      { key: "blocked", label: "拦截结果", desc: "是否被拦截" },
      { key: "log_type", label: "日志类型", desc: "防护 / 访问 / 审计" },
      { key: "site_id", label: "站点", desc: "按站点聚合" },
    ],
  },
  {
    label: "网络与地理",
    items: [
      { key: "client_ip", label: "客户端 IP", desc: "ip.src" },
      { key: "tcp_ip", label: "直连 IP", desc: "ip.tcp（TCP 连接地址）" },
      { key: "ip_is_private", label: "IP 是否内网", desc: "ip.src.is_private" },
      { key: "scheme", label: "协议", desc: "net.scheme" },
      { key: "http_version", label: "HTTP 版本", desc: "http.version" },
      { key: "geo_country", label: "IP 国家/地区", desc: "geo.country" },
      { key: "geo_region", label: "IP 省/州", desc: "geo.region" },
      { key: "geo_city", label: "IP 城市", desc: "geo.city" },
      { key: "geo_asn", label: "IP ASN", desc: "geo.asn" },
      { key: "geo_isp", label: "运营商 ISP", desc: "geo.isp" },
      { key: "xff_first", label: "X-Forwarded-For", desc: "http.xff 首跳" },
    ],
  },
  {
    label: "URL 与路径",
    items: [
      { key: "domain", label: "请求域名", desc: "http.host" },
      { key: "full_url", label: "完整 URL", desc: "http.url" },
      { key: "request_uri", label: "原始请求行", desc: "http.request_uri" },
      { key: "uri_path", label: "请求路径", desc: "http.uri.path" },
      { key: "uri_ext", label: "文件后缀", desc: "http.uri.ext" },
      { key: "uri_depth", label: "路径深度", desc: "http.uri.depth" },
      { key: "uri_pattern", label: "路径模式", desc: "归一化路径（仅日志）" },
      { key: "uri_query", label: "原始查询串", desc: "http.uri.query" },
      { key: "query_count_bucket", label: "查询参数个数", desc: "http.query.count 分段" },
    ],
  },
  {
    label: "HTTP 请求",
    items: [
      { key: "method", label: "请求方法", desc: "http.method" },
      { key: "referer_host", label: "Referer", desc: "http.referer 主机名" },
      { key: "ua", label: "User-Agent", desc: "http.ua" },
      { key: "cookie_name", label: "Cookie 参数名", desc: "http.cookie 键" },
      { key: "cookie_count_bucket", label: "Cookie 个数", desc: "http.cookie.count 分段" },
    ],
  },
  {
    label: "客户端识别",
    items: [
      { key: "bot_name", label: "Bot 名称", desc: "bot.name" },
      { key: "bot_category", label: "Bot 分类", desc: "bot.category" },
      { key: "ua_family", label: "UA 类型", desc: "ua.family" },
      { key: "ua_os", label: "操作系统", desc: "ua.os" },
      { key: "ua_browser", label: "浏览器", desc: "UA 解析浏览器" },
      { key: "tls_version", label: "TLS 版本", desc: "tls.version" },
      { key: "tls_ja3", label: "JA3 指纹", desc: "tls.ja3" },
    ],
  },
  {
    label: "时间与流量",
    items: [
      { key: "hour_of_day", label: "当前小时", desc: "derived.time.hour" },
      { key: "weekday", label: "星期几", desc: "derived.time.weekday" },
    ],
  },
] as const satisfies readonly LogStatsDimensionGroup[];
