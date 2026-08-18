import { LOG_HIT_CATEGORY, logStatsDimensionLayout } from "@/constants/logDimensionLayout";
import {
  formatGeoAsn,
  formatGeoCity,
  formatGeoCountry,
  formatGeoIsp,
  formatGeoRegion,
  geoAsnSelectOptions,
  geoCitySelectOptions,
  geoCountrySelectOptions,
  geoRegionSelectOptions,
  GEO_COUNTRY_LABELS as geoCountryLabel,
  GEO_ISP_SELECT_HINTS,
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

/** 命中趋势图：已知防护方式的展示色（新方式自动回退到备用色板） */
export const modeChartColor: Record<string, string> = {
  block: "#ef4444",
  js_challenge: "#a855f7",
  captcha: "#f59e0b",
  slide_captcha: "#06b6d4",
  observe: "#3b82f6",
  unknown: "#94a3b8",
};

const MODE_TREND_ORDER = [
  "block",
  "js_challenge",
  "captcha",
  "slide_captcha",
  "observe",
] as const;

const FALLBACK_CHART_COLORS = [
  "#8b5cf6",
  "#14b8a6",
  "#f97316",
  "#ec4899",
  "#84cc16",
  "#0ea5e9",
];

export type TrendModeSeriesItem = { key: string; name: string; color: string };

export type TrendPoint = {
  time?: string;
  by_mode?: Record<string, number>;
  [key: string]: unknown;
};

export type TrendModeMeta = string | { mode: string; label?: string };

function orderModeKeys(keys: string[]): string[] {
  const set = new Set(keys);
  const ordered = MODE_TREND_ORDER.filter((k) => set.has(k));
  const rest = [...set]
    .filter((k) => !(MODE_TREND_ORDER as readonly string[]).includes(k) && k !== "unknown")
    .sort();
  if (set.has("unknown")) rest.push("unknown");
  return [...ordered, ...rest];
}

export function trendModeValue(row: TrendPoint, key: string): number {
  if (row.by_mode && row.by_mode[key] !== undefined) {
    return Number(row.by_mode[key] || 0);
  }
  return Number(row[key] ?? 0);
}

/**
 * 按防护方式构建趋势系列：包含时间段内出现过的全部 mode（含未来新增），
 * 全程为 0 的不展示。优先使用后端 trend_modes。
 */
export function buildTrendModeSeries(
  trend: TrendPoint[],
  trendModes?: TrendModeMeta[],
): TrendModeSeriesItem[] {
  const labelByMode = new Map<string, string>();
  let keys: string[] = [];

  if (trendModes?.length) {
    for (const item of trendModes) {
      if (typeof item === "string") {
        keys.push(item);
      } else if (item?.mode) {
        keys.push(item.mode);
        if (item.label) labelByMode.set(item.mode, item.label);
      }
    }
  } else {
    const totals = new Map<string, number>();
    for (const row of trend) {
      const bm = row.by_mode;
      if (bm && typeof bm === "object") {
        for (const [k, v] of Object.entries(bm)) {
          totals.set(k, (totals.get(k) || 0) + Number(v || 0));
        }
      } else {
        for (const k of MODE_TREND_ORDER) {
          const v = Number(row[k] ?? 0);
          if (v) totals.set(k, (totals.get(k) || 0) + v);
        }
      }
    }
    keys = [...totals.entries()].filter(([, n]) => n > 0).map(([k]) => k);
  }

  keys = keys.filter((k) => trend.some((row) => trendModeValue(row, k) > 0));
  keys = orderModeKeys(keys);

  return keys.map((key, i) => ({
    key,
    name: labelByMode.get(key) || modeLabel[key] || key,
    color: modeChartColor[key] || FALLBACK_CHART_COLORS[i % FALLBACK_CHART_COLORS.length],
  }));
}

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
    case "geo_region":
      return formatGeoRegion(key || label) || label;
    case "geo_city":
      return formatGeoCity(key || label) || label;
    case "geo_asn":
      return formatGeoAsn(key || label) || label;
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

export function negateFilterOperator(op: LogFilterOperator): LogFilterOperator {
  switch (op) {
    case "eq":
      return "ne";
    case "ne":
      return "eq";
    case "contains":
      return "not_contains";
    case "not_contains":
      return "contains";
    case "like":
      return "not_contains";
    default:
      return "ne";
  }
}

export function withFilterMode(
  conditions: LogFilterCondition[],
  mode: "include" | "exclude",
): LogFilterCondition[] {
  if (mode === "include") return conditions;
  return conditions.map((condition) => ({
    ...condition,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    operator: negateFilterOperator(condition.operator),
  }));
}

export interface LogFilterCondition {
  id: string;
  field: string;
  operator: LogFilterOperator;
  value: string | string[];
  arg?: string;
}

const BOOL_FILTER_KEYS = new Set(["blocked", "ip_is_private"]);
const MULTI_VALUE_SELECT_KEYS = new Set([
  "source",
  "mode",
  "log_type",
  "geo_country",
  "geo_region",
  "geo_city",
  "geo_asn",
  "geo_isp",
  "method",
  "scheme",
  "http_version",
  "bot_category",
  "ua_family",
  "query_count_bucket",
  "cookie_count_bucket",
  "weekday",
  "hour_of_day",
]);

/** 可搜索下拉 + 手输自定义值（与规则条件编辑器一致） */
const SUGGEST_FILTER_KEYS = new Set([
  "geo_region",
  "geo_city",
  "geo_asn",
  "geo_isp",
]);

export function getOperatorsForField(field: LogFilterFieldDef): LogFilterOperator[] {
  if (field.type === "bool") return ["eq", "ne"];
  if (field.type === "select") return ["eq", "ne"];
  if (field.type === "number" || field.type === "rule_id" || field.type === "site") return ["eq", "ne"];
  if (field.type === "cookie") return ["eq", "contains", "ne", "not_contains", "like"];
  if (field.key === "keyword") return ["contains", "not_contains", "like"];
  return ["eq", "contains", "ne", "not_contains", "like"];
}

export function defaultOperatorForField(field: LogFilterFieldDef): LogFilterOperator {
  return getOperatorsForField(field)[0];
}

export function supportsMultiValue(field: LogFilterFieldDef): boolean {
  return field.type === "select" && MULTI_VALUE_SELECT_KEYS.has(field.key);
}

export function isSuggestFilterField(field: LogFilterFieldDef): boolean {
  return field.type === "select" && SUGGEST_FILTER_KEYS.has(field.key);
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
    arg: field.type === "cookie" ? "" : undefined,
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
  if (field.type === "cookie" && !(condition.arg || "").trim()) return false;
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
    if (field.key === "geo_region") {
      return formatGeoRegion(raw) || raw;
    }
    if (field.key === "geo_city") {
      return formatGeoCity(raw) || raw;
    }
    if (field.key === "geo_asn") {
      return formatGeoAsn(raw) || raw;
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
  const argLabel =
    field.type === "cookie" && condition.arg
      ? ` (${condition.arg})`
      : "";
  return `${field.label}${argLabel} ${op} ${valueLabel}`;
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
        ...(condition.arg?.trim() ? { arg: condition.arg.trim() } : {}),
      };
    })
    .filter((item): item is { field: string; op: LogFilterOperator; value: string | string[]; arg?: string } => !!item);
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
      const n = Number(primary);
      if (!Number.isFinite(n)) continue;
      (filters as Record<string, number | undefined>)[field.key] = n;
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
      if (field.key === "geo_asn") {
        const n = Number(primary);
        if (Number.isFinite(n)) filters.geo_asn = n;
        continue;
      }
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
      const value = (filters as Record<string, number | undefined>)[field.key];
      if (value === undefined) continue;
      conditions.push({
        id: createFilterCondition(field.key).id,
        field: field.key,
        operator: "eq",
        value: String(value),
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
      if (field.key === "geo_asn") {
        if (filters.geo_asn === undefined) continue;
        conditions.push({
          id: createFilterCondition(field.key).id,
          field: field.key,
          operator: "eq",
          value: String(filters.geo_asn),
        });
        continue;
      }
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
      operator:
        field.key === "keyword" || field.key === "rule_name" || field.key === "ua"
          ? "contains"
          : "eq",
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
  86400: "24 小时",
};

export type LogFilterFieldType = "text" | "select" | "bool" | "number" | "site" | "rule_id" | "cookie";

export interface LogFilterFieldDef {
  key: string;
  label: string;
  type: LogFilterFieldType;
  placeholder?: string;
  argPlaceholder?: string;
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
  { value: "http", label: "HTTP" },
  { value: "https", label: "HTTPS" },
];

export const httpVersionOptions = [
  { value: "1.0", label: "HTTP/1.0" },
  { value: "1.1", label: "HTTP/1.1" },
  { value: "2.0", label: "HTTP/2" },
  { value: "3.0", label: "HTTP/3" },
];

export const boolFilterOptions = [
  { value: "true", label: "是" },
  { value: "false", label: "否" },
];

export const uaFamilyOptions = [
  { value: "browser", label: "浏览器" },
  { value: "bot", label: "Bot" },
];

export const queryCountBucketOptions = [
  { value: "0", label: "0" },
  { value: "1-5", label: "1-5" },
  { value: "6-20", label: "6-20" },
  { value: "20+", label: "20+" },
];

export const weekdayOptions = [
  { value: "1", label: "周一" },
  { value: "2", label: "周二" },
  { value: "3", label: "周三" },
  { value: "4", label: "周四" },
  { value: "5", label: "周五" },
  { value: "6", label: "周六" },
  { value: "7", label: "周日" },
];

export const hourOfDayOptions = Array.from({ length: 24 }, (_, hour) => ({
  value: String(hour),
  label: `${hour}:00`,
}));

export const geoCountryOptions = geoCountrySelectOptions();
export const geoRegionOptions = geoRegionSelectOptions();
export const geoCityOptions = geoCitySelectOptions();
export const geoAsnOptions = geoAsnSelectOptions();
export const geoIspOptions = GEO_ISP_SELECT_HINTS.map((item) => ({
  value: item.value,
  label: item.label,
}));

/** 筛选专用字段：不在统计维度中，追加到对应分组末尾 */
const LOG_FILTER_GROUP_EXTRAS: Record<string, string[]> = {
  [LOG_HIT_CATEGORY]: ["rule_name", "action", "keyword"],
  "HTTP 请求": ["cookie"],
};

const logFilterFieldRegistry: Record<string, LogFilterFieldDef> = {
  rule_id: { key: "rule_id", label: "命中规则", type: "rule_id" },
  source: { key: "source", label: "防护来源", type: "select", options: selectFromRecord(sourceLabel) },
  mode: { key: "mode", label: "防护方式", type: "select", options: selectFromRecord(modeLabel) },
  blocked: { key: "blocked", label: "拦截结果", type: "bool" },
  log_type: { key: "log_type", label: "日志类型", type: "select", options: selectFromRecord(logTypeLabel) },
  site_id: { key: "site_id", label: "站点", type: "site" },
  rule_name: { key: "rule_name", label: "规则名称", type: "text", placeholder: "模糊匹配" },
  action: { key: "action", label: "动作", type: "text", placeholder: "action" },
  keyword: { key: "keyword", label: "关键字", type: "text", placeholder: "URL / UA / 域名模糊搜索" },
  client_ip: { key: "client_ip", label: "客户端 IP", type: "text", placeholder: "精确匹配" },
  tcp_ip: { key: "tcp_ip", label: "直连 IP", type: "text", placeholder: "精确匹配" },
  ip_is_private: { key: "ip_is_private", label: "IP 是否内网", type: "bool" },
  scheme: { key: "scheme", label: "协议", type: "select", options: schemeOptions },
  http_version: { key: "http_version", label: "HTTP 版本", type: "select", options: httpVersionOptions },
  geo_country: { key: "geo_country", label: "IP 国家/地区", type: "select", options: geoCountryOptions },
  geo_region: {
    key: "geo_region",
    label: "IP 省/州",
    type: "select",
    options: geoRegionOptions,
    placeholder: "选择或输入代码，如 GD",
  },
  geo_city: {
    key: "geo_city",
    label: "IP 城市",
    type: "select",
    options: geoCityOptions,
    placeholder: "选择或输入英文名",
  },
  geo_asn: {
    key: "geo_asn",
    label: "IP ASN",
    type: "select",
    options: geoAsnOptions,
    placeholder: "选择或输入 ASN 数字",
  },
  geo_isp: {
    key: "geo_isp",
    label: "运营商 ISP",
    type: "select",
    options: geoIspOptions,
    placeholder: "选择或输入组织名",
  },
  xff_first: { key: "xff_first", label: "X-Forwarded-For", type: "text", placeholder: "XFF 首跳 IP" },
  domain: { key: "domain", label: "请求域名", type: "text", placeholder: "精确匹配" },
  full_url: { key: "full_url", label: "完整 URL", type: "text", placeholder: "如 https://example.com/api" },
  request_uri: { key: "request_uri", label: "原始请求行", type: "text", placeholder: "如 /api?id=1" },
  uri_path: { key: "uri_path", label: "请求路径", type: "text", placeholder: "精确匹配" },
  uri_ext: { key: "uri_ext", label: "文件后缀", type: "text", placeholder: "如 php / js" },
  uri_depth: { key: "uri_depth", label: "路径深度", type: "number", placeholder: "如 3" },
  uri_pattern: { key: "uri_pattern", label: "路径模式", type: "text", placeholder: "归一化路径" },
  uri_query: { key: "uri_query", label: "原始查询串", type: "text", placeholder: "如 id=1&foo=bar" },
  query_count_bucket: {
    key: "query_count_bucket",
    label: "查询参数个数",
    type: "select",
    options: queryCountBucketOptions,
  },
  method: { key: "method", label: "请求方法", type: "select", options: httpMethodOptions },
  referer_host: { key: "referer_host", label: "Referer", type: "text", placeholder: "Referer 主机名" },
  ua: { key: "ua", label: "User-Agent", type: "text", placeholder: "模糊匹配" },
  cookie_name: { key: "cookie_name", label: "Cookie 参数名", type: "text", placeholder: "如 PHPSESSID" },
  cookie_count_bucket: {
    key: "cookie_count_bucket",
    label: "Cookie 个数",
    type: "select",
    options: queryCountBucketOptions,
  },
  cookie: {
    key: "cookie",
    label: "Cookie 参数值",
    type: "cookie",
    argPlaceholder: "参数名",
    placeholder: "参数值",
  },
  bot_name: { key: "bot_name", label: "Bot 名称", type: "text", placeholder: "如 Googlebot" },
  bot_category: { key: "bot_category", label: "Bot 分类", type: "select", options: [] },
  ua_family: { key: "ua_family", label: "UA 类型", type: "select", options: uaFamilyOptions },
  ua_os: { key: "ua_os", label: "操作系统", type: "text", placeholder: "精确匹配" },
  ua_browser: { key: "ua_browser", label: "浏览器", type: "text", placeholder: "精确匹配" },
  tls_version: { key: "tls_version", label: "TLS 版本", type: "text", placeholder: "如 TLSv1.3" },
  tls_ja3: { key: "tls_ja3", label: "JA3 指纹", type: "text", placeholder: "精确匹配" },
  hour_of_day: { key: "hour_of_day", label: "当前小时", type: "select", options: hourOfDayOptions },
  weekday: { key: "weekday", label: "星期几", type: "select", options: weekdayOptions },
};

function buildLogDetailFilterGroups(): { label: string; fields: LogFilterFieldDef[] }[] {
  return logStatsDimensionLayout.map((group) => {
    const keys = [
      ...group.items.map((item) => item.key),
      ...(LOG_FILTER_GROUP_EXTRAS[group.label] || []),
    ];
    const fields = keys
      .map((key) => logFilterFieldRegistry[key])
      .filter((field): field is LogFilterFieldDef => !!field);
    return { label: group.label, fields };
  });
}

/** 与 `logStatsDimensionLayout` 顺序/分类对齐；防护命中与 HTTP 请求含筛选专用字段 */
export const logDetailFilterGroups = buildLogDetailFilterGroups();

/** Most-used log detail filters shown in the compact top row. */
export const logDetailQuickFilterKeys = [
  "source",
  "mode",
  "blocked",
  "site_id",
  "client_ip",
  "tcp_ip",
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
  if (filters.geo_asn !== undefined) return true;
  if (filters.method) return true;
  if (filters.scheme) return true;
  if (filters.http_version) return true;
  if (filters.domain) return true;
  if (filters.full_url) return true;
  if (filters.request_uri) return true;
  if (filters.uri_path) return true;
  if (filters.uri_ext) return true;
  if (filters.uri_depth !== undefined) return true;
  if (filters.uri_pattern) return true;
  if (filters.uri_query) return true;
  if (filters.query_count_bucket) return true;
  if (filters.cookie_name) return true;
  if (filters.cookie_count_bucket) return true;
  if (filters.referer_host) return true;
  if (filters.ua) return true;
  if (filters.ua_family) return true;
  if (filters.bot_name) return true;
  if (filters.bot_category) return true;
  if (filters.ua_os) return true;
  if (filters.ua_browser) return true;
  if (filters.tls_version) return true;
  if (filters.tls_ja3) return true;
  if (filters.hour_of_day) return true;
  if (filters.weekday) return true;
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
  tcp_ip: string;
  ip_is_private?: boolean;
  xff_first: string;
  geo_country?: string;
  geo_region: string;
  geo_city: string;
  geo_isp: string;
  geo_asn?: number;
  method?: string;
  scheme?: string;
  http_version?: string;
  domain: string;
  full_url: string;
  request_uri: string;
  uri_path: string;
  uri_ext: string;
  uri_depth?: number;
  uri_pattern: string;
  uri_query: string;
  query_count_bucket?: string;
  cookie_name: string;
  cookie_count_bucket?: string;
  referer_host: string;
  keyword: string;
  ua: string;
  ua_family: string;
  bot_name: string;
  bot_category: string;
  ua_os: string;
  ua_browser: string;
  tls_version: string;
  tls_ja3: string;
  hour_of_day?: string;
  weekday?: string;
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
    tcp_ip: "",
    ip_is_private: undefined,
    xff_first: "",
    geo_country: undefined,
    geo_region: "",
    geo_city: "",
    geo_isp: "",
    geo_asn: undefined,
    method: undefined,
    scheme: undefined,
    http_version: undefined,
    domain: "",
    full_url: "",
    request_uri: "",
    uri_path: "",
    uri_ext: "",
    uri_depth: undefined,
    uri_pattern: "",
    uri_query: "",
    query_count_bucket: undefined,
    cookie_name: "",
    cookie_count_bucket: undefined,
    referer_host: "",
    keyword: "",
    ua: "",
    ua_family: "",
    bot_name: "",
    bot_category: "",
    ua_os: "",
    ua_browser: "",
    tls_version: "",
    tls_ja3: "",
    hour_of_day: undefined,
    weekday: undefined,
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
    tcp_ip: filters.tcp_ip || undefined,
    xff_first: filters.xff_first || undefined,
    geo_region: filters.geo_region || undefined,
    geo_city: filters.geo_city || undefined,
    geo_isp: filters.geo_isp || undefined,
    domain: filters.domain || undefined,
    full_url: filters.full_url || undefined,
    request_uri: filters.request_uri || undefined,
    uri_path: filters.uri_path || undefined,
    uri_ext: filters.uri_ext || undefined,
    uri_depth: filters.uri_depth,
    uri_pattern: filters.uri_pattern || undefined,
    uri_query: filters.uri_query || undefined,
    query_count_bucket: filters.query_count_bucket || undefined,
    cookie_count_bucket: filters.cookie_count_bucket || undefined,
    referer_host: filters.referer_host || undefined,
    keyword: filters.keyword || undefined,
    ua: filters.ua || undefined,
    ua_family: filters.ua_family || undefined,
    bot_name: filters.bot_name || undefined,
    bot_category: filters.bot_category || undefined,
    ua_os: filters.ua_os || undefined,
    ua_browser: filters.ua_browser || undefined,
    tls_version: filters.tls_version || undefined,
    tls_ja3: filters.tls_ja3 || undefined,
    hour_of_day:
      filters.hour_of_day !== undefined && filters.hour_of_day !== ""
        ? Number(filters.hour_of_day)
        : undefined,
    weekday:
      filters.weekday !== undefined && filters.weekday !== ""
        ? Number(filters.weekday)
        : undefined,
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
  tcp_ip: { field: "tcp_ip" },
  ip_is_private: { field: "ip_is_private" },
  xff_first: { field: "xff_first" },
  geo_country: { field: "geo_country" },
  geo_region: { field: "geo_region" },
  geo_city: { field: "geo_city" },
  geo_isp: { field: "geo_isp" },
  geo_asn: { field: "geo_asn" },
  method: { field: "method" },
  scheme: { field: "scheme" },
  http_version: { field: "http_version" },
  domain: { field: "domain" },
  full_url: { field: "full_url" },
  request_uri: { field: "request_uri" },
  uri_path: { field: "uri_path" },
  uri_ext: { field: "uri_ext" },
  uri_depth: { field: "uri_depth" },
  uri_pattern: { field: "uri_pattern" },
  uri_query: { field: "uri_query" },
  query_count_bucket: { field: "query_count_bucket" },
  cookie_name: { field: "cookie_name" },
  cookie_count_bucket: { field: "cookie_count_bucket" },
  referer_host: { field: "referer_host" },
  ua: { field: "ua", operator: "contains" },
  ua_family: { field: "ua_family" },
  bot_name: { field: "bot_name" },
  bot_category: { field: "bot_category" },
  ua_os: { field: "ua_os" },
  ua_browser: { field: "ua_browser" },
  tls_version: { field: "tls_version" },
  tls_ja3: { field: "tls_ja3" },
  hour_of_day: { field: "hour_of_day" },
  weekday: { field: "weekday" },
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

  const operator = mapping.operator || defaultOperatorForField(field);
  const value = supportsMultiValue(field) ? [key] : key;

  return [
    {
      ...createFilterCondition(mapping.field),
      field: mapping.field,
      operator,
      value,
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
    case "tcp_ip":
      filters.tcp_ip = key;
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
    case "uri_depth":
      filters.uri_depth = Number(key);
      break;
    case "uri_pattern":
      filters.uri_pattern = key;
      break;
    case "query_count_bucket":
      filters.query_count_bucket = key;
      break;
    case "cookie_name":
      filters.cookie_name = key;
      break;
    case "cookie_count_bucket":
      filters.cookie_count_bucket = key;
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
    case "tls_ja3":
      filters.tls_ja3 = key;
      break;
    case "hour_of_day":
      filters.hour_of_day = key;
      break;
    case "weekday":
      filters.weekday = key;
      break;
    case "full_url":
      filters.full_url = key;
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
