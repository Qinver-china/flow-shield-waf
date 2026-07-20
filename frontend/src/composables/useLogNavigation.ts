import { useRouter } from "vue-router";

export interface LogNavQuery {
  tab?: "stats" | "detail";
  preset?: "30m" | "1h" | "6h" | "24h" | "today" | "yesterday" | "3d" | "7d" | "14d" | "30d" | "custom";
  dimension?: string;
  blocked?: boolean;
  mode?: string;
  source?: string;
  log_type?: string;
  client_ip?: string;
  rule_id?: number;
  site_id?: number;
  bot_name?: string;
  bot_category?: string;
  geo_country?: string;
  method?: string;
  keyword?: string;
}

function toQueryString(filters: LogNavQuery): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.tab) query.tab = filters.tab;
  if (filters.preset) query.preset = filters.preset;
  if (filters.dimension) query.dimension = filters.dimension;
  if (filters.blocked !== undefined) query.blocked = String(filters.blocked);
  if (filters.mode) query.mode = filters.mode;
  if (filters.source) query.source = filters.source;
  if (filters.log_type) query.log_type = filters.log_type;
  if (filters.client_ip) query.client_ip = filters.client_ip;
  if (filters.rule_id) query.rule_id = String(filters.rule_id);
  if (filters.site_id) query.site_id = String(filters.site_id);
  if (filters.bot_name) query.bot_name = filters.bot_name;
  if (filters.bot_category) query.bot_category = filters.bot_category;
  if (filters.geo_country) query.geo_country = filters.geo_country;
  if (filters.method) query.method = filters.method;
  if (filters.keyword) query.keyword = filters.keyword;
  return query;
}

/** 从总览等页面跳转到防护日志，并带上筛选条件 */
export function useLogNavigation(defaultPreset: LogNavQuery["preset"] = "6h") {
  const router = useRouter();

  function goToLogs(filters: LogNavQuery = {}) {
    router.push({
      path: "/logs",
      query: toQueryString({ preset: defaultPreset, ...filters }),
    });
  }

  return { goToLogs };
}
