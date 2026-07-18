export const modeLabel: Record<string, string> = {
  observe: "观察",
  block: "拦截",
  captcha: "数学计算验证",
  js_challenge: "JS 挑战",
  slide_captcha: "滑动验证",
  unknown: "未知",
};

export const modeColor: Record<string, string> = {
  observe: "blue",
  block: "red",
  captcha: "orange",
  js_challenge: "purple",
  slide_captcha: "cyan",
};

export const botCategoryLabel: Record<string, string> = {
  search_engine: "搜索引擎",
  monitoring: "监控探测",
  social: "社交平台",
  seo_tool: "SEO 工具",
  scraper: "通用爬虫",
  malicious: "恶意 Bot",
  other: "其他",
};

export const sourceLabel: Record<string, string> = {
  ratelimit: "速率防护",
  rule: "自定义规则",
  blacklist: "黑名单",
  whitelist: "白名单",
  bot: "Bot 库",
};

export const logTypeLabel: Record<string, string> = {
  protection: "防护命中",
  "access-control": "访问控制",
  audit: "审计",
};

export const geoCountryLabel: Record<string, string> = {
  CN: "中国",
  US: "美国",
  HK: "中国香港",
  TW: "中国台湾",
  MO: "中国澳门",
  JP: "日本",
  KR: "韩国",
  SG: "新加坡",
  GB: "英国",
  DE: "德国",
  FR: "法国",
  RU: "俄罗斯",
  IN: "印度",
  AU: "澳大利亚",
  CA: "加拿大",
  NL: "荷兰",
  VN: "越南",
  TH: "泰国",
  MY: "马来西亚",
  ID: "印度尼西亚",
  PH: "菲律宾",
  BR: "巴西",
  IT: "意大利",
  ES: "西班牙",
  SE: "瑞典",
  CH: "瑞士",
  AE: "阿联酋",
  UNKNOWN: "未知",
  XX: "未知",
};

export function formatStatsValueLabel(
  dimension: StatsDimension,
  key: string,
  label: string,
  opts?: { formatSiteId?: (id: number | null | undefined) => string },
): string {
  if (key === "none" || label === "（空）") return "（空）";
  switch (dimension) {
    case "site_id": {
      if (key !== "none" && opts?.formatSiteId) {
        const formatted = opts.formatSiteId(Number(key));
        if (formatted && !formatted.startsWith("#")) return formatted;
      }
      return label;
    }
    case "source":
      return sourceLabel[key] || sourceLabel[label] || label;
    case "mode":
      return modeLabel[key] || modeLabel[label] || label;
    case "log_type":
      return logTypeLabel[key] || logTypeLabel[label] || label;
    case "blocked":
      return key === "true" ? "已拦截" : "已放行";
    case "geo_country": {
      const code = (key || label).toUpperCase();
      return geoCountryLabel[code] || label;
    }
    case "ua":
    case "full_url":
      return label;
    case "bot_category":
      return botCategoryLabel[key] || botCategoryLabel[label] || label;
    default:
      return label;
  }
}

export function localizeStatsItems(
  dimension: StatsDimension,
  items: any[],
  opts?: { formatSiteId?: (id: number | null | undefined) => string },
) {
  return items.map((item) => ({
    ...item,
    label: formatStatsValueLabel(dimension, item.key, item.label, opts),
  }));
}

export const statsDimensionGroups = [
  {
    label: "核心",
    items: [
      { key: "rule_id", label: "命中规则", desc: "按规则 ID 聚合" },
      { key: "source", label: "防护来源", desc: "规则 / 黑名单 / 限速等" },
      { key: "mode", label: "防护模式", desc: "观察 / 拦截 / 人机等" },
      { key: "blocked", label: "拦截结果", desc: "已拦截 vs 已放行" },
      { key: "log_type", label: "日志类型", desc: "防护 / 访问 / 审计" },
      { key: "site_id", label: "站点", desc: "按站点 ID 聚合（名称实时解析）" },
    ],
  },
  {
    label: "网络与地理",
    items: [
      { key: "client_ip", label: "客户端 IP", desc: "按来源 IP 聚合" },
      { key: "ip_is_private", label: "内网 IP", desc: "是否内网地址" },
      { key: "xff_first", label: "XFF 首跳", desc: "X-Forwarded-For 第一个 IP" },
      { key: "geo_country", label: "国家/地区", desc: "按 IP 地理位置聚合" },
      { key: "geo_region", label: "省/州", desc: "地理区域" },
      { key: "geo_city", label: "城市", desc: "地理城市" },
      { key: "geo_isp", label: "运营商", desc: "ISP" },
      { key: "geo_ip_type", label: "IP 类型", desc: "机房 / 家庭等" },
      { key: "geo_asn", label: "ASN", desc: "自治系统号" },
    ],
  },
  {
    label: "HTTP / URL",
    items: [
      { key: "method", label: "请求方法", desc: "GET / POST 等" },
      { key: "scheme", label: "协议", desc: "http / https" },
      { key: "http_version", label: "HTTP 版本", desc: "1.0 / 1.1 / 2" },
      { key: "domain", label: "域名", desc: "按请求域名聚合" },
      { key: "full_url", label: "完整 URL", desc: "协议 + 域名 + 路径与查询串" },
      { key: "uri_path", label: "请求路径", desc: "URI path" },
      { key: "uri_ext", label: "文件后缀", desc: "如 php / js" },
      { key: "uri_depth", label: "路径深度", desc: "路径段数量" },
      { key: "uri_pattern", label: "路径模式", desc: "归一化后的路径" },
      { key: "referer_host", label: "Referer 主机", desc: "来源页域名" },
      { key: "query_count_bucket", label: "参数数量", desc: "查询参数个数分段" },
    ],
  },
  {
    label: "客户端",
    items: [
      { key: "ua", label: "User-Agent", desc: "完整 UA 字符串（Top 命中）" },
      { key: "ua_family", label: "UA 类型", desc: "浏览器 / Bot" },
      { key: "bot_name", label: "Bot 名称", desc: "命中的已知 Bot" },
      { key: "bot_category", label: "Bot 分类", desc: "搜索引擎 / 爬虫等" },
      { key: "ua_os", label: "操作系统", desc: "OS 分布" },
      { key: "ua_browser", label: "浏览器", desc: "浏览器分布" },
      { key: "tls_version", label: "TLS 版本", desc: "TLS 协议版本" },
      { key: "tls_ja3", label: "JA3 指纹", desc: "TLS 指纹" },
    ],
  },
  {
    label: "时间",
    items: [
      { key: "hour_of_day", label: "小时分布", desc: "0-23 点" },
      { key: "weekday", label: "星期分布", desc: "周一至周日" },
    ],
  },
] as const;

export const statsDimensions = statsDimensionGroups.flatMap((g) => g.items);

export type StatsDimension = (typeof statsDimensions)[number]["key"];

export type TimePreset = "24h" | "7d" | "30d" | "custom";

export const timePresets: { key: TimePreset; label: string; hours: number }[] = [
  { key: "24h", label: "近 24 小时", hours: 24 },
  { key: "7d", label: "近 7 天", hours: 168 },
  { key: "30d", label: "近 30 天", hours: 720 },
  { key: "custom", label: "自定义", hours: 0 },
];

export const trafficWindowLabels: Record<number, string> = {
  10: "10 秒",
  30: "30 秒",
  60: "1 分钟",
  300: "5 分钟",
  1800: "30 分钟",
  3600: "60 分钟",
};

export type LogFilterFieldType = "text" | "select" | "bool" | "number" | "site" | "rule_id";

export interface LogFilterFieldDef {
  key: string;
  label: string;
  type: LogFilterFieldType;
  placeholder?: string;
  options?: { value: string; label: string }[];
}

const selectFromRecord = (record: Record<string, string>) =>
  Object.entries(record).map(([value, label]) => ({ value, label }));

export const httpMethodOptions = [
  { value: "GET", label: "GET" },
  { value: "POST", label: "POST" },
  { value: "PUT", label: "PUT" },
  { value: "PATCH", label: "PATCH" },
  { value: "DELETE", label: "DELETE" },
  { value: "HEAD", label: "HEAD" },
  { value: "OPTIONS", label: "OPTIONS" },
];

export const schemeOptions = [
  { value: "http", label: "http" },
  { value: "https", label: "https" },
];

export const httpVersionOptions = [
  { value: "1.0", label: "HTTP/1.0" },
  { value: "1.1", label: "HTTP/1.1" },
  { value: "2.0", label: "HTTP/2" },
];

export const boolFilterOptions = [
  { value: "true", label: "是" },
  { value: "false", label: "否" },
];

export const geoCountryOptions = selectFromRecord(geoCountryLabel);

export const logDetailFilterGroups: { label: string; fields: LogFilterFieldDef[] }[] = [
  {
    label: "核心",
    fields: [
      { key: "source", label: "防护来源", type: "select", options: selectFromRecord(sourceLabel) },
      { key: "mode", label: "防护模式", type: "select", options: selectFromRecord(modeLabel) },
      { key: "log_type", label: "日志类型", type: "select", options: selectFromRecord(logTypeLabel) },
      { key: "blocked", label: "拦截结果", type: "bool" },
      { key: "site_id", label: "站点", type: "site" },
      { key: "rule_id", label: "规则 ID", type: "rule_id" },
      { key: "rule_name", label: "规则名称", type: "text", placeholder: "模糊匹配" },
      { key: "action", label: "动作", type: "text", placeholder: "action" },
    ],
  },
  {
    label: "网络与地理",
    fields: [
      { key: "client_ip", label: "客户端 IP", type: "text", placeholder: "精确匹配" },
      { key: "ip_is_private", label: "内网 IP", type: "bool" },
      { key: "xff_first", label: "XFF 首跳", type: "text", placeholder: "精确匹配" },
      { key: "geo_country", label: "国家/地区", type: "select", options: geoCountryOptions },
      { key: "geo_region", label: "省/州", type: "text", placeholder: "精确匹配" },
      { key: "geo_city", label: "城市", type: "text", placeholder: "精确匹配" },
      { key: "geo_isp", label: "运营商", type: "text", placeholder: "精确匹配" },
      { key: "geo_ip_type", label: "IP 类型", type: "text", placeholder: "如 datacenter / residential" },
      { key: "geo_asn", label: "ASN", type: "number" },
    ],
  },
  {
    label: "HTTP / URL",
    fields: [
      { key: "method", label: "请求方法", type: "select", options: httpMethodOptions },
      { key: "scheme", label: "协议", type: "select", options: schemeOptions },
      { key: "http_version", label: "HTTP 版本", type: "select", options: httpVersionOptions },
      { key: "domain", label: "域名", type: "text", placeholder: "精确匹配" },
      { key: "uri_path", label: "请求路径", type: "text", placeholder: "精确匹配" },
      { key: "uri_ext", label: "文件后缀", type: "text", placeholder: "如 php / js" },
      { key: "referer_host", label: "Referer 主机", type: "text", placeholder: "精确匹配" },
      { key: "keyword", label: "关键字", type: "text", placeholder: "URL / UA / 域名模糊搜索" },
    ],
  },
  {
    label: "客户端",
    fields: [
      { key: "ua", label: "User-Agent", type: "text", placeholder: "模糊匹配" },
      { key: "ua_family", label: "UA 类型", type: "text", placeholder: "如 browser / bot" },
      { key: "bot_name", label: "Bot 名称", type: "text", placeholder: "如 Googlebot" },
      { key: "bot_category", label: "Bot 分类", type: "select", options: [] },
      { key: "ua_os", label: "操作系统", type: "text", placeholder: "精确匹配" },
      { key: "ua_browser", label: "浏览器", type: "text", placeholder: "精确匹配" },
      { key: "tls_version", label: "TLS 版本", type: "text", placeholder: "如 TLSv1.3" },
    ],
  },
];

/** Most-used log detail filters shown in the compact top row. */
export const logDetailQuickFilterKeys = [
  "source",
  "mode",
  "blocked",
  "site_id",
  "client_ip",
  "rule_id",
  "keyword",
] as const;

const allLogFilterFields = () =>
  logDetailFilterGroups.flatMap((group) => group.fields);

export function resolveLogFilterFields(keys: readonly string[]): LogFilterFieldDef[] {
  const fieldMap = new Map(allLogFilterFields().map((field) => [field.key, field]));
  return keys.map((key) => fieldMap.get(key)).filter((field): field is LogFilterFieldDef => !!field);
}

export const logDetailQuickFilterFields = resolveLogFilterFields(logDetailQuickFilterKeys);

const quickFilterKeySet = new Set<string>(logDetailQuickFilterKeys);

export function buildAdvancedLogFilterGroups() {
  return logDetailFilterGroups
    .map((group) => ({
      ...group,
      fields: group.fields.filter((field) => !quickFilterKeySet.has(field.key)),
    }))
    .filter((group) => group.fields.length > 0);
}

export function logDetailFiltersUseAdvanced(filters: LogDetailFilters): boolean {
  if (filters.log_type) return true;
  if (filters.rule_name) return true;
  if (filters.action) return true;
  if (filters.ip_is_private !== undefined) return true;
  if (filters.xff_first) return true;
  if (filters.geo_country) return true;
  if (filters.geo_region) return true;
  if (filters.geo_city) return true;
  if (filters.geo_isp) return true;
  if (filters.geo_ip_type) return true;
  if (filters.geo_asn !== undefined) return true;
  if (filters.method) return true;
  if (filters.scheme) return true;
  if (filters.http_version) return true;
  if (filters.domain) return true;
  if (filters.uri_path) return true;
  if (filters.uri_ext) return true;
  if (filters.referer_host) return true;
  if (filters.ua) return true;
  if (filters.ua_family) return true;
  if (filters.bot_name) return true;
  if (filters.bot_category) return true;
  if (filters.ua_os) return true;
  if (filters.ua_browser) return true;
  if (filters.tls_version) return true;
  return false;
}

export type LogDetailFilters = {
  source?: string;
  mode?: string;
  log_type?: string;
  blocked?: boolean;
  site_id?: number;
  rule_id?: number;
  rule_name: string;
  action: string;
  client_ip: string;
  ip_is_private?: boolean;
  xff_first: string;
  geo_country?: string;
  geo_region: string;
  geo_city: string;
  geo_isp: string;
  geo_ip_type: string;
  geo_asn?: number;
  method?: string;
  scheme?: string;
  http_version?: string;
  domain: string;
  uri_path: string;
  uri_ext: string;
  referer_host: string;
  keyword: string;
  ua: string;
  ua_family: string;
  bot_name: string;
  bot_category: string;
  ua_os: string;
  ua_browser: string;
  tls_version: string;
};

export function createDefaultLogFilters(): LogDetailFilters {
  return {
    source: undefined,
    mode: undefined,
    log_type: undefined,
    blocked: undefined,
    site_id: undefined,
    rule_id: undefined,
    rule_name: "",
    action: "",
    client_ip: "",
    ip_is_private: undefined,
    xff_first: "",
    geo_country: undefined,
    geo_region: "",
    geo_city: "",
    geo_isp: "",
    geo_ip_type: "",
    geo_asn: undefined,
    method: undefined,
    scheme: undefined,
    http_version: undefined,
    domain: "",
    uri_path: "",
    uri_ext: "",
    referer_host: "",
    keyword: "",
    ua: "",
    ua_family: "",
    bot_name: "",
    bot_category: "",
    ua_os: "",
    ua_browser: "",
    tls_version: "",
  };
}

export function buildLogQueryParams(
  filters: LogDetailFilters,
  paging: { page: number; page_size: number },
  range?: { start?: string; end?: string },
): Record<string, unknown> {
  const params: Record<string, unknown> = {
    page: paging.page,
    page_size: paging.page_size,
    source: filters.source,
    mode: filters.mode,
    log_type: filters.log_type,
    blocked: filters.blocked,
    site_id: filters.site_id,
    rule_id: filters.rule_id,
    geo_country: filters.geo_country,
    method: filters.method,
    scheme: filters.scheme,
    http_version: filters.http_version,
    ip_is_private: filters.ip_is_private,
    geo_asn: filters.geo_asn,
    rule_name: filters.rule_name || undefined,
    action: filters.action || undefined,
    client_ip: filters.client_ip || undefined,
    xff_first: filters.xff_first || undefined,
    geo_region: filters.geo_region || undefined,
    geo_city: filters.geo_city || undefined,
    geo_isp: filters.geo_isp || undefined,
    geo_ip_type: filters.geo_ip_type || undefined,
    domain: filters.domain || undefined,
    uri_path: filters.uri_path || undefined,
    uri_ext: filters.uri_ext || undefined,
    referer_host: filters.referer_host || undefined,
    keyword: filters.keyword || undefined,
    ua: filters.ua || undefined,
    ua_family: filters.ua_family || undefined,
    bot_name: filters.bot_name || undefined,
    bot_category: filters.bot_category || undefined,
    ua_os: filters.ua_os || undefined,
    ua_browser: filters.ua_browser || undefined,
    tls_version: filters.tls_version || undefined,
  };
  if (range?.start) params.start = range.start;
  if (range?.end) params.end = range.end;
  return params;
}

export function applyStatsDrillDownToFilters(
  dim: StatsDimension,
  key: string,
  filters: LogDetailFilters,
): void {
  if (key === "none") return;
  switch (dim) {
    case "rule_id": {
      const sep = key.indexOf(":");
      if (sep > 0) {
        filters.source = key.slice(0, sep);
        filters.rule_id = Number(key.slice(sep + 1));
      } else {
        filters.rule_id = Number(key);
      }
      break;
    }
    case "client_ip":
      filters.client_ip = key;
      break;
    case "source":
      filters.source = key;
      break;
    case "mode":
      filters.mode = key;
      break;
    case "site_id":
      filters.site_id = Number(key);
      break;
    case "blocked":
      filters.blocked = key === "true";
      break;
    case "log_type":
      filters.log_type = key;
      break;
    case "domain":
      filters.domain = key;
      break;
    case "geo_country":
      filters.geo_country = key;
      break;
    case "method":
      filters.method = key;
      break;
    case "ip_is_private":
      filters.ip_is_private = key === "true" || key === "1";
      break;
    case "xff_first":
      filters.xff_first = key;
      break;
    case "geo_region":
      filters.geo_region = key;
      break;
    case "geo_city":
      filters.geo_city = key;
      break;
    case "geo_isp":
      filters.geo_isp = key;
      break;
    case "geo_ip_type":
      filters.geo_ip_type = key;
      break;
    case "geo_asn":
      filters.geo_asn = Number(key);
      break;
    case "scheme":
      filters.scheme = key;
      break;
    case "http_version":
      filters.http_version = key;
      break;
    case "uri_path":
      filters.uri_path = key;
      break;
    case "uri_ext":
      filters.uri_ext = key;
      break;
    case "referer_host":
      filters.referer_host = key;
      break;
    case "ua":
      filters.ua = key;
      break;
    case "ua_family":
      filters.ua_family = key;
      break;
    case "bot_name":
      filters.bot_name = key;
      break;
    case "bot_category":
      filters.bot_category = key;
      break;
    case "ua_os":
      filters.ua_os = key;
      break;
    case "ua_browser":
      filters.ua_browser = key;
      break;
    case "tls_version":
      filters.tls_version = key;
      break;
    case "full_url":
      filters.keyword = key;
      break;
    default:
      break;
  }
}

export async function hydrateBotCategoryFilterOptions() {
  const { api } = await import("@/api");
  try {
    const resp = await api.get("/api/v1/bot-categories/options");
    const options = (resp.data || []).map((item: { value: string; label: string }) => ({
      label: item.label,
      value: item.value,
    }));
    for (const group of logDetailFilterGroups) {
      const field = group.fields.find((f) => f.key === "bot_category");
      if (field && field.type === "select") {
        field.options = options;
      }
    }
    for (const item of options) {
      botCategoryLabel[item.value] = item.label;
    }
  } catch {
    // keep static fallbacks when API unavailable
  }
}
