import { logStatsDimensionLayout } from "@/constants/logDimensionLayout";
import {
  formatGeoCountry,
  formatGeoIsp,
  geoCountrySelectOptions,
  GEO_COUNTRY_LABELS as geoCountryLabel,
} from "@/utils/geoLabels";

export { geoCountryLabel };

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
};

export const logTypeLabel: Record<string, string> = {
  protection: "防护命中",
  "access-control": "访问控制",
  audit: "审计",
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
      return formatGeoCountry(key || label) || label;
    }
    case "geo_isp":
      return formatGeoIsp(key || label) || label;
    case "ua":
    case "full_url":
    case "request_uri":
    case "uri_query":
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

export const statsDimensionGroups = logStatsDimensionLayout;

export const statsDimensions = statsDimensionGroups.flatMap((g) => g.items);

export type StatsDimension = (typeof statsDimensions)[number]["key"];

export type TimePreset =
  | "30m"
  | "1h"
  | "6h"
  | "24h"
  | "today"
  | "yesterday"
  | "3d"
  | "7d"
  | "14d"
  | "30d"
  | "custom";

export type TimePresetKind = "hours" | "today" | "yesterday" | "custom";

export interface TimePresetDef {
  key: TimePreset;
  label: string;
  kind: TimePresetKind;
  hours?: number;
}

export const timePresets: TimePresetDef[] = [
  { key: "30m", label: "近 30 分钟", kind: "hours", hours: 0.5 },
  { key: "1h", label: "近 1 小时", kind: "hours", hours: 1 },
  { key: "6h", label: "近 6 小时", kind: "hours", hours: 6 },
  { key: "24h", label: "近 24 小时", kind: "hours", hours: 24 },
  { key: "today", label: "今日", kind: "today" },
  { key: "yesterday", label: "昨日", kind: "yesterday" },
  { key: "3d", label: "近 3 日", kind: "hours", hours: 72 },
  { key: "7d", label: "近 7 日", kind: "hours", hours: 168 },
  { key: "14d", label: "近 14 日", kind: "hours", hours: 336 },
  { key: "30d", label: "近 30 日", kind: "hours", hours: 720 },
  { key: "custom", label: "自定义", kind: "custom" },
];

export type TrendGranularity = "1m" | "5m" | "10m" | "30m" | "1h" | "1d" | "1w" | "1mo";

export interface TrendGranularityOption {
  key: TrendGranularity;
  label: string;
}

export const trendGranularityOptions: TrendGranularityOption[] = [
  { key: "1m", label: "1 分钟" },
  { key: "5m", label: "5 分钟" },
  { key: "10m", label: "10 分钟" },
  { key: "30m", label: "30 分钟" },
  { key: "1h", label: "1 小时" },
  { key: "1d", label: "1 天" },
  { key: "1w", label: "1 周" },
  { key: "1mo", label: "1 个月" },
];

const presetTrendGranularity: Partial<Record<TimePreset, TrendGranularity>> = {
  "30m": "5m",
  "6h": "10m",
  "24h": "1h",
};

export function resolveAutoTrendGranularity(
  preset: TimePreset,
  rangeMinutes: number,
): TrendGranularity {
  if (presetTrendGranularity[preset]) {
    return presetTrendGranularity[preset]!;
  }
  if (rangeMinutes <= 30) return "5m";
  if (rangeMinutes <= 360) return "10m";
  if (rangeMinutes <= 1440) return "1h";
  if (rangeMinutes <= 10080) return "1d";
  if (rangeMinutes <= 43200) return "1w";
  return "1mo";
}

export type LogFilterOperator = "eq" | "ne" | "contains" | "not_contains" | "like";

export const logFilterOperators: { value: LogFilterOperator; label: string }[] = [
  { value: "eq", label: "等于" },
  { value: "contains", label: "包含" },
  { value: "ne", label: "不等于" },
  { value: "not_contains", label: "不包含" },
  { value: "like", label: "模糊匹配" },
];

export interface LogFilterCondition {
  id: string;
  field: string;
  operator: LogFilterOperator;
  value: string | string[];
}

const BOOL_FILTER_KEYS = new Set(["blocked", "ip_is_private"]);
const MULTI_VALUE_SELECT_KEYS = new Set([
  "source",
  "mode",
  "log_type",
  "geo_country",
  "method",
  "scheme",
  "http_version",
  "bot_category",
]);

export function getOperatorsForField(field: LogFilterFieldDef): LogFilterOperator[] {
  if (field.type === "bool") return ["eq", "ne"];
  if (field.type === "select") return ["eq", "ne"];
  if (field.type === "number" || field.type === "rule_id" || field.type === "site") return ["eq", "ne"];
  if (field.key === "keyword") return ["contains", "not_contains", "like"];
  return ["eq", "contains", "ne", "not_contains", "like"];
}

export function defaultOperatorForField(field: LogFilterFieldDef): LogFilterOperator {
  return getOperatorsForField(field)[0];
}

export function supportsMultiValue(field: LogFilterFieldDef): boolean {
  return field.type === "select" && MULTI_VALUE_SELECT_KEYS.has(field.key);
}

export function allLogFilterFieldDefs(): LogFilterFieldDef[] {
  return logDetailFilterGroups.flatMap((group) => group.fields);
}

export function findLogFilterField(key: string): LogFilterFieldDef | undefined {
  return allLogFilterFieldDefs().find((field) => field.key === key);
}

export function createFilterCondition(fieldKey?: string): LogFilterCondition {
  const field = findLogFilterField(fieldKey || "source") || allLogFilterFieldDefs()[0];
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    field: field.key,
    operator: defaultOperatorForField(field),
    value: supportsMultiValue(field) ? [] : "",
  };
}

function normalizeConditionValue(field: LogFilterFieldDef, value: string | string[]): string | string[] {
  if (Array.isArray(value)) {
    return value.map((item) => item.trim()).filter(Boolean);
  }
  if (field.type === "bool") {
    if (value === "true" || value === "false") return value;
    return value.trim();
  }
  return value.trim();
}

export function isConditionComplete(condition: LogFilterCondition): boolean {
  const field = findLogFilterField(condition.field);
  if (!field) return false;
  const value = normalizeConditionValue(field, condition.value);
  if (Array.isArray(value)) return value.length > 0;
  return value !== "";
}

export function formatConditionLabel(condition: LogFilterCondition): string {
  const field = findLogFilterField(condition.field);
  if (!field) return condition.field;
  const op = logFilterOperators.find((item) => item.value === condition.operator)?.label || condition.operator;
  const value = normalizeConditionValue(field, condition.value);
  const formatValue = (raw: string) => {
    if (field.type === "select" && field.options) {
      return field.options.find((item) => item.value === raw)?.label || raw;
    }
    if (field.key === "geo_isp") {
      return formatGeoIsp(raw) || raw;
    }
    if (field.type === "bool") {
      if (raw === "true") return field.key === "blocked" ? "已拦截" : "是";
      if (raw === "false") return field.key === "blocked" ? "已放行" : "否";
    }
    return raw;
  };
  const valueLabel = Array.isArray(value)
    ? value.map(formatValue).join("、")
    : formatValue(String(value));
  return `${field.label} ${op} ${valueLabel}`;
}

export function conditionsToFiltersJson(conditions: LogFilterCondition[]): string | undefined {
  const items = conditions
    .filter(isConditionComplete)
    .map((condition) => {
      const field = findLogFilterField(condition.field);
      if (!field) return null;
      const value = normalizeConditionValue(field, condition.value);
      return {
        field: condition.field,
        op: condition.operator,
        value,
      };
    })
    .filter((item): item is { field: string; op: LogFilterOperator; value: string | string[] } => !!item);
  return items.length ? JSON.stringify(items) : undefined;
}

export function conditionsToLogDetailFilters(conditions: LogFilterCondition[]): LogDetailFilters {
  const filters = createDefaultLogFilters();
  for (const condition of conditions) {
    if (!isConditionComplete(condition)) continue;
    const field = findLogFilterField(condition.field);
    if (!field) continue;
    const value = normalizeConditionValue(field, condition.value);
    const primary = Array.isArray(value) ? value[0] : value;
    if (field.type === "bool") {
      filters[field.key as "blocked" | "ip_is_private"] = primary === "true";
      continue;
    }
    if (field.type === "number") {
      filters.geo_asn = Number(primary);
      continue;
    }
    if (field.type === "rule_id") {
      filters.rule_id = Number(primary);
      continue;
    }
    if (field.type === "site") {
      filters.site_id = Number(primary);
      continue;
    }
    if (field.type === "select") {
      (filters as Record<string, string | undefined>)[field.key] = primary;
      continue;
    }
    (filters as Record<string, string>)[field.key] = primary;
  }
  return filters;
}

export function logDetailFiltersToConditions(filters: LogDetailFilters): LogFilterCondition[] {
  const conditions: LogFilterCondition[] = [];
  for (const field of allLogFilterFieldDefs()) {
    if (field.type === "bool") {
      const value = filters[field.key as "blocked" | "ip_is_private"];
      if (value === undefined) continue;
      conditions.push({
        id: createFilterCondition(field.key).id,
        field: field.key,
        operator: "eq",
        value: value ? "true" : "false",
      });
      continue;
    }
    if (field.type === "number") {
      if (filters.geo_asn === undefined) continue;
      conditions.push({
        id: createFilterCondition(field.key).id,
        field: field.key,
        operator: "eq",
        value: String(filters.geo_asn),
      });
      continue;
    }
    if (field.type === "rule_id") {
      if (filters.rule_id === undefined) continue;
      conditions.push({
        id: createFilterCondition(field.key).id,
        field: field.key,
        operator: "eq",
        value: String(filters.rule_id),
      });
      continue;
    }
    if (field.type === "site") {
      if (filters.site_id === undefined) continue;
      conditions.push({
        id: createFilterCondition(field.key).id,
        field: field.key,
        operator: "eq",
        value: String(filters.site_id),
      });
      continue;
    }
    if (field.type === "select") {
      const value = (filters as Record<string, string | undefined>)[field.key];
      if (!value) continue;
      conditions.push({
        id: createFilterCondition(field.key).id,
        field: field.key,
        operator: "eq",
        value,
      });
      continue;
    }
    const textValue = (filters as Record<string, string>)[field.key];
    if (!textValue) continue;
    conditions.push({
      id: createFilterCondition(field.key).id,
      field: field.key,
      operator: field.key === "keyword" || field.key === "rule_name" || field.key === "ua" ? "contains" : "eq",
      value: textValue,
    });
  }
  return conditions;
}

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

export const geoCountryOptions = geoCountrySelectOptions();

export const logDetailFilterGroups: { label: string; fields: LogFilterFieldDef[] }[] = [
  {
    label: "防护命中",
    fields: [
      { key: "source", label: "防护来源", type: "select", options: selectFromRecord(sourceLabel) },
      { key: "mode", label: "防护方式", type: "select", options: selectFromRecord(modeLabel) },
      { key: "log_type", label: "日志类型", type: "select", options: selectFromRecord(logTypeLabel) },
      { key: "blocked", label: "拦截结果", type: "bool" },
      { key: "site_id", label: "站点", type: "site" },
      { key: "rule_id", label: "命中规则", type: "rule_id" },
      { key: "rule_name", label: "规则名称", type: "text", placeholder: "模糊匹配" },
      { key: "action", label: "动作", type: "text", placeholder: "action" },
      { key: "keyword", label: "关键字", type: "text", placeholder: "URL / UA / 域名模糊搜索" },
    ],
  },
  {
    label: "网络与地理",
    fields: [
      { key: "client_ip", label: "客户端 IP", type: "text", placeholder: "精确匹配" },
      { key: "ip_is_private", label: "IP 是否内网", type: "bool" },
      { key: "scheme", label: "协议", type: "select", options: schemeOptions },
      { key: "http_version", label: "HTTP 版本", type: "select", options: httpVersionOptions },
      { key: "geo_country", label: "IP 国家/地区", type: "select", options: geoCountryOptions },
      { key: "geo_region", label: "IP 省/州", type: "text", placeholder: "代码，如 GD / VA" },
      { key: "geo_city", label: "IP 城市", type: "text", placeholder: "英文名，如 Beijing" },
      { key: "geo_asn", label: "IP ASN", type: "number" },
      { key: "geo_isp", label: "运营商 ISP", type: "text", placeholder: "精确匹配组织名，如 Amazon.com, Inc." },
      { key: "geo_ip_type", label: "IP 类型", type: "text", placeholder: "如 datacenter / residential" },
      { key: "xff_first", label: "X-Forwarded-For", type: "text", placeholder: "XFF 首跳 IP" },
    ],
  },
  {
    label: "URL 与路径",
    fields: [
      { key: "domain", label: "请求域名", type: "text", placeholder: "精确匹配" },
      { key: "request_uri", label: "原始请求行", type: "text", placeholder: "如 /api?id=1" },
      { key: "uri_path", label: "请求路径", type: "text", placeholder: "精确匹配" },
      { key: "uri_ext", label: "文件后缀", type: "text", placeholder: "如 php / js" },
      { key: "uri_query", label: "原始查询串", type: "text", placeholder: "如 id=1&foo=bar" },
    ],
  },
  {
    label: "HTTP 请求",
    fields: [
      { key: "method", label: "请求方法", type: "select", options: httpMethodOptions },
      { key: "referer_host", label: "Referer", type: "text", placeholder: "Referer 主机名" },
      { key: "ua", label: "User-Agent", type: "text", placeholder: "模糊匹配" },
    ],
  },
  {
    label: "客户端识别",
    fields: [
      { key: "bot_name", label: "Bot 名称", type: "text", placeholder: "如 Googlebot" },
      { key: "bot_category", label: "Bot 分类", type: "select", options: [] },
      { key: "ua_family", label: "UA 类型", type: "text", placeholder: "如 browser / bot" },
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
  if (filters.request_uri) return true;
  if (filters.uri_path) return true;
  if (filters.uri_ext) return true;
  if (filters.uri_query) return true;
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
  request_uri: string;
  uri_path: string;
  uri_ext: string;
  uri_query: string;
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
    request_uri: "",
    uri_path: "",
    uri_ext: "",
    uri_query: "",
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
  conditions?: LogFilterCondition[],
): Record<string, unknown> {
  const filtersJson = conditions ? conditionsToFiltersJson(conditions) : undefined;
  if (filtersJson) {
    const params: Record<string, unknown> = {
      page: paging.page,
      page_size: paging.page_size,
      filters: filtersJson,
    };
    if (range?.start) params.start = range.start;
    if (range?.end) params.end = range.end;
    return params;
  }

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
    request_uri: filters.request_uri || undefined,
    uri_path: filters.uri_path || undefined,
    uri_ext: filters.uri_ext || undefined,
    uri_query: filters.uri_query || undefined,
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

export const LOG_SOURCE_API: Record<string, string> = {
  rule: "/api/v1/rules",
  blacklist: "/api/v1/blacklist",
  whitelist: "/api/v1/whitelist",
  ratelimit: "/api/v1/ratelimit",
  bot: "/api/v1/bots",
};

export const LOG_SOURCE_PAGE: Record<string, string> = {
  rule: "/rules",
  blacklist: "/blacklist",
  whitelist: "/whitelist",
  ratelimit: "/ratelimit",
  bot: "/bots",
};

export const LOG_API_PAGE: Record<string, string> = {
  "/api/v1/rules": "/rules",
  "/api/v1/blacklist": "/blacklist",
  "/api/v1/whitelist": "/whitelist",
  "/api/v1/ratelimit": "/ratelimit",
  "/api/v1/bots": "/bots",
  "/api/v1/sites": "/sites",
};

export type ResourceDrawerMode = "view" | "edit";

export function getResourcePagePath(apiBase: string): string | null {
  return LOG_API_PAGE[apiBase] || null;
}

export function buildResourceDrawerLocation(
  apiBase: string,
  id: number,
  mode: ResourceDrawerMode = "view",
) {
  const path = getResourcePagePath(apiBase);
  if (!path || !Number.isFinite(id)) return null;
  return {
    path,
    query: {
      id: String(id),
      drawer: mode,
    },
  };
}

export function parseRuleStatsKey(key: string): { source?: string; ruleId?: number } {
  const sep = key.indexOf(":");
  if (sep > 0) {
    const ruleId = Number(key.slice(sep + 1));
    return {
      source: key.slice(0, sep),
      ruleId: Number.isFinite(ruleId) ? ruleId : undefined,
    };
  }
  const ruleId = Number(key);
  return Number.isFinite(ruleId) ? { ruleId } : {};
}

export type LogResourceViewTarget =
  | { kind: "api"; apiBase: string; id: number; title: string }
  | { kind: "bot_by_name"; name: string; title: string }
  | { kind: "route"; path: string; title: string };

const STATS_DIM_FILTER: Partial<Record<StatsDimension, { field: string; operator?: LogFilterOperator }>> = {
  source: { field: "source" },
  mode: { field: "mode" },
  blocked: { field: "blocked" },
  log_type: { field: "log_type" },
  site_id: { field: "site_id" },
  client_ip: { field: "client_ip" },
  ip_is_private: { field: "ip_is_private" },
  xff_first: { field: "xff_first" },
  geo_country: { field: "geo_country" },
  geo_region: { field: "geo_region" },
  geo_city: { field: "geo_city" },
  geo_isp: { field: "geo_isp" },
  geo_ip_type: { field: "geo_ip_type" },
  geo_asn: { field: "geo_asn" },
  method: { field: "method" },
  scheme: { field: "scheme" },
  http_version: { field: "http_version" },
  domain: { field: "domain" },
  request_uri: { field: "request_uri" },
  uri_path: { field: "uri_path" },
  uri_ext: { field: "uri_ext" },
  uri_query: { field: "uri_query" },
  referer_host: { field: "referer_host" },
  ua: { field: "ua", operator: "contains" },
  ua_family: { field: "ua_family" },
  bot_name: { field: "bot_name" },
  bot_category: { field: "bot_category" },
  ua_os: { field: "ua_os" },
  ua_browser: { field: "ua_browser" },
  tls_version: { field: "tls_version" },
  full_url: { field: "keyword", operator: "contains" },
};

export function buildConditionsFromStatsDimension(
  dimension: StatsDimension,
  key: string,
): LogFilterCondition[] {
  if (!key || key === "none") return [];

  if (dimension === "rule_id") {
    const parsed = parseRuleStatsKey(key);
    const conditions: LogFilterCondition[] = [];
    if (parsed.source) {
      conditions.push({
        ...createFilterCondition("source"),
        field: "source",
        operator: "eq",
        value: parsed.source,
      });
    }
    if (parsed.ruleId !== undefined) {
      conditions.push({
        ...createFilterCondition("rule_id"),
        field: "rule_id",
        operator: "eq",
        value: String(parsed.ruleId),
      });
    }
    return conditions;
  }

  const mapping = STATS_DIM_FILTER[dimension];
  if (!mapping) return [];

  const field = findLogFilterField(mapping.field);
  if (!field) return [];

  return [
    {
      ...createFilterCondition(mapping.field),
      field: mapping.field,
      operator: mapping.operator || defaultOperatorForField(field),
      value: key,
    },
  ];
}

export function buildConditionsFromLogRule(record: {
  source?: string | null;
  rule_id?: number | null;
}): LogFilterCondition[] {
  if (!record.rule_id) return [];
  const key = record.source ? `${record.source}:${record.rule_id}` : String(record.rule_id);
  return buildConditionsFromStatsDimension("rule_id", key);
}

export function getResourceViewTarget(
  dimension: StatsDimension,
  key: string,
  label: string,
): LogResourceViewTarget | null {
  if (!key || key === "none") return null;

  if (dimension === "rule_id") {
    const parsed = parseRuleStatsKey(key);
    if (!parsed.ruleId) return null;
    const source = parsed.source || "rule";
    const apiBase = LOG_SOURCE_API[source];
    if (!apiBase) return null;
    return {
      kind: "api",
      apiBase,
      id: parsed.ruleId,
      title: label || `规则 #${parsed.ruleId}`,
    };
  }

  if (dimension === "site_id") {
    const siteId = Number(key);
    if (!Number.isFinite(siteId)) return null;
    return {
      kind: "api",
      apiBase: "/api/v1/sites",
      id: siteId,
      title: label || `站点 #${siteId}`,
    };
  }

  if (dimension === "bot_name") {
    return {
      kind: "bot_by_name",
      name: key,
      title: label || key,
    };
  }

  if (dimension === "source") {
    const path = LOG_SOURCE_PAGE[key];
    if (!path) return null;
    const sourceTitle = sourceLabel[key] || key;
    return {
      kind: "route",
      path,
      title: sourceTitle,
    };
  }

  return null;
}

export function getResourceViewLabel(dimension: StatsDimension, key: string): string {
  if (dimension === "rule_id") return "查看当前规则";
  if (dimension === "site_id") return "查看站点";
  if (dimension === "bot_name") return "查看 Bot";
  if (dimension === "source") {
    const sourceTitle = sourceLabel[key] || key;
    return `查看${sourceTitle}`;
  }
  return "查看详情";
}

export function getResourceEditLabel(source: string): string {
  const labels: Record<string, string> = {
    rule: "编辑规则",
    blacklist: "编辑黑名单",
    whitelist: "编辑白名单",
    ratelimit: "编辑限速规则",
    bot: "编辑 Bot",
    site: "编辑站点",
  };
  return labels[source] || "编辑";
}

export function getResourceViewTargetFromLogRule(record: {
  source?: string | null;
  rule_id?: number | null;
  rule_name?: string | null;
}): LogResourceViewTarget | null {
  if (!record.rule_id) return null;
  const key = record.source ? `${record.source}:${record.rule_id}` : String(record.rule_id);
  return getResourceViewTarget("rule_id", key, record.rule_name || `规则 #${record.rule_id}`);
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
    case "request_uri":
      filters.request_uri = key;
      break;
    case "uri_query":
      filters.uri_query = key;
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
