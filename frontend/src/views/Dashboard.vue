<template>
  <div class="dashboard-page fs-page">
    <div class="page-hero">
      <div class="hero-main">
        <div class="hero-heading">
          <span class="hero-icon" aria-hidden="true">
            <dashboard-outlined />
          </span>
          <div class="hero-text">
            <div class="hero-title-row">
              <h2 class="hero-title">安全总览</h2>
              <span class="hero-desc">24 小时防护态势</span>
            </div>
            <div class="hero-health">
              <div class="health-item" v-for="item in healthItems" :key="item.key">
                <span class="health-dot" :class="item.status" />
                <span class="health-text">
                  {{ item.label }} {{ item.status === "ok" ? "正常" : "异常" }}
                </span>
              </div>
              <a-tag
                v-if="feed.pending_ai_incidents > 0"
                color="orange"
                class="health-ai-link"
                @click="goAiGuard"
              >
                {{ feed.pending_ai_incidents }} 条 AI 分析待处理
              </a-tag>
            </div>
          </div>
        </div>
      </div>
      <div class="hero-actions">
        <div class="hero-time">{{ statsWindowLabel }}</div>
        <dashboard-live-refresh-toggle />
      </div>
    </div>

    <h3 class="fs-section-title"><appstore-outlined /> 防护配置</h3>
    <a-row :gutter="[12, 12]">
      <a-col v-for="item in resourceCards" :key="item.key" :xs="12" :sm="8" :md="6" :xl="4">
        <stat-card
          clickable
          :label="item.label"
          :value="item.value"
          :sub="item.sub"
          :color="item.color"
          :icon="item.icon"
          @click="onResourceCardClick(item.key)"
        />
      </a-col>
    </a-row>

    <h3 class="fs-section-title"><safety-outlined /> 近 24 小时安全态势</h3>
    <a-row :gutter="[12, 12]">
      <a-col v-for="item in securityCards" :key="item.key" :xs="12" :sm="8" :md="8" :xl="4">
        <stat-card
          large
          clickable
          :label="item.label"
          :value="item.value"
          :sub="item.sub"
          :color="item.color"
          :value-color="item.valueColor"
          :icon="item.icon"
          :delta="item.delta"
          @click="onSecurityCardClick(item.key)"
        />
      </a-col>
    </a-row>
    <a-row :gutter="[12, 12]">
      <a-col :xs="24" :md="14">
        <a-card class="panel-card traffic-metrics-panel" :bordered="false">
          <template #title>
            <span class="panel-title"><thunderbolt-outlined /> {{ trafficCardTitle }}</span>
            <a-tag v-if="traffic.burst_active" color="orange" style="margin-left: 8px">自动取证中</a-tag>
          </template>
          <template #extra>
            <site-single-select v-model:value="trafficSiteId" class="traffic-site-filter" />
          </template>
          <a-row class="traffic-metrics-grid" :gutter="[8, 8]">
            <a-col v-for="w in traffic.windows" :key="w.sec" :xs="12" :sm="8" :md="8" :lg="4" :xl="4">
              <div class="metric-window-card traffic-window">
                <div class="metric-window-label">{{ windowLabel(w.sec) }}</div>
                <div class="metric-window-value">
                  {{ w.requests }}
                  <span class="metric-window-meta">{{ Number(w.qps || 0).toFixed(1) }} QPS</span>
                </div>
                <a-progress v-if="w.threshold" :percent="Math.min(100, Math.round((w.requests / w.threshold) * 100))"
                  size="small" :stroke-color="progressColor(w.requests, w.threshold)" :show-info="false"
                  class="metric-window-progress" />
              </div>
            </a-col>
          </a-row>
        </a-card>
      </a-col>
      <a-col :xs="24" :md="10">
        <a-card class="panel-card intel-card traffic-metrics-panel" :bordered="false">
          <template #title>
            <span class="panel-title"><alert-outlined /> 流量异常检测</span>
          </template>
          <template #extra>
            <site-single-select v-model:value="trafficSiteId" class="traffic-site-filter" />
          </template>
          <a-empty v-if="!intelDisplayWindows.length" description="暂无数据" />
          <a-row v-else class="traffic-metrics-grid" :gutter="[8, 8]">
            <a-col v-for="w in intelDisplayWindows" :key="w.window_sec" :xs="12" :sm="12" :md="12" :lg="6" :xl="6">
              <div class="metric-window-card intel-item" :class="{ anomaly: w.is_anomaly }">
                <div class="metric-window-label">{{ w.label }}</div>
                <div class="metric-window-value">
                  {{ w.current_requests }}
                  <span class="metric-window-meta">请求</span>
                </div>
                <div class="metric-window-sub">
                  <template v-if="w.baseline_avg != null">
                    基线 {{ formatIntelBaseline(w.baseline_avg) }}
                    <span v-if="w.baseline_warmup" class="intel-warmup">· 学习中</span>
                    <span v-else-if="w.deviation_ratio != null" class="intel-deviation">
                      · {{ formatIntelDeviation(w.deviation_ratio) }}
                    </span>
                  </template>
                  <template v-else>暂无基线</template>
                </div>
              </div>
            </a-col>
          </a-row>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[12, 12]">
      <a-col :xs="24" :xl="14">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title panel-title-link" @click.stop="goLogs()">
              <line-chart-outlined /> 命中趋势
            </span>
          </template>
          <div ref="trendEl" class="chart-box chart-box-lg" />
        </a-card>
      </a-col>
      <a-col :xs="24" :xl="10">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><pie-chart-outlined /> 防护方式分布</span>
          </template>
          <div ref="modeEl" class="chart-box chart-box-lg" />
        </a-card>
      </a-col>
      <a-col :xs="24" :md="12" :xl="8">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><bar-chart-outlined /> 防护来源</span>
          </template>
          <div ref="sourceEl" class="chart-box" />
        </a-card>
      </a-col>
      <a-col :xs="24" :md="12" :xl="8">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><global-outlined /> 拦截来源国家 Top</span>
          </template>
          <div ref="countryEl" class="chart-box" />
        </a-card>
      </a-col>
      <a-col :xs="24" :md="24" :xl="8">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><file-text-outlined /> 日志类型</span>
          </template>
          <div ref="logTypeEl" class="chart-box" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[12, 12]">
      <a-col :xs="24" :lg="6">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><alert-outlined /> Top 命中规则</span>
          </template>
          <a-table class="feed-list-body"
            :columns="ruleCols"
            :data-source="stats.top_rules"
            :pagination="false"
            :row-key="(record: { id?: number; name: string }) => String(record.id ?? record.name)"
            size="small"
            bordered
            :scroll="{ x: 180 }"
            :custom-row="ruleTableRow"
          />
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="6">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><aim-outlined /> Top 攻击 IP</span>
          </template>
          <a-table class="feed-list-body"
            :columns="ipCols"
            :data-source="stats.top_ips"
            :pagination="false"
            row-key="ip"
            size="small"
            bordered
            :scroll="{ x: 180 }"
            :custom-row="ipTableRow"
          />
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="12">
        <a-card class="panel-card feed-card" :bordered="false">
          <template #title>
            <span class="panel-title"><bell-outlined /> 最新动态</span>
          </template>
          <div class="feed-list-body">
            <a-spin :spinning="feedLoading">
              <a-empty v-if="!feed.items.length && !feedLoading" description="暂无动态" />
              <ul v-else class="feed-timeline">
                <li
                  v-for="item in feed.items"
                  :key="item.id"
                  class="feed-timeline-item"
                  :class="`feed-timeline-item--${feedTone(item)}`"
                  @click="onFeedClick(item)"
                >
                  <span class="feed-timeline-dot" aria-hidden="true" />
                  <div class="feed-timeline-main">
                    <div class="feed-timeline-top">
                      <span class="feed-timeline-tag">{{ feedTypeLabel(item.type) }}</span>
                      <span class="feed-timeline-title">{{ item.title }}</span>
                      <span class="feed-timeline-time">{{ formatFeedTime(item.created_at) }}</span>
                    </div>
                    <div v-if="feedMeta(item)" class="feed-timeline-meta">{{ feedMeta(item) }}</div>
                  </div>
                </li>
              </ul>
            </a-spin>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  AimOutlined,
  AlertOutlined,
  AppstoreOutlined,
  BarChartOutlined,
  BellOutlined,
  CheckCircleOutlined,
  ClusterOutlined,
  DashboardOutlined,
  DisconnectOutlined,
  FileTextOutlined,
  GlobalOutlined,
  LineChartOutlined,
  PieChartOutlined,
  SafetyCertificateOutlined,
  SafetyOutlined,
  StopOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons-vue";
import * as echarts from "echarts";
import type { ECharts } from "echarts";
import { storeToRefs } from "pinia";
import { api } from "@/api";
import StatCard from "@/components/StatCard.vue";
import SiteSingleSelect from "@/components/SiteSingleSelect.vue";
import DashboardLiveRefreshToggle from "@/components/DashboardLiveRefreshToggle.vue";
import { useLogNavigation } from "@/composables/useLogNavigation";
import { useSiteOptions } from "@/composables/useSiteOptions";
import { useDashboardLiveRefresh } from "@/composables/useDashboardLiveRefresh";
import { echartsThemeName } from "@/composables/useEchartsTheme";
import { useAppSettingsStore } from "@/stores/appSettings";
import { useThemeStore } from "@/stores/theme";
import { formatClockTime, formatDateTime, formatDateTimeShort } from "@/utils/datetime";
import { lineAreaGradient } from "@/utils/lineAreaGradient";
import { trafficWindowLabels } from "@/views/logs/constants";

interface CountPair {
  total: number;
  enabled?: number;
}

interface OverviewCounts {
  sites: CountPair;
  rules: CountPair;
  blacklist: CountPair;
  whitelist: CountPair;
  exceptions: CountPair;
  ratelimits: CountPair;
  certificates: { total: number };
}

interface SummaryData {
  blocked_delta_pct?: number | null;
  passed_delta_pct?: number | null;
  total_requests_delta_pct?: number | null;
  unique_ips_delta_pct?: number | null;
}

const themeStore = useThemeStore();
const { isDark } = storeToRefs(themeStore);
const appSettings = useAppSettingsStore();
const router = useRouter();
const { goToLogs } = useLogNavigation("24h");
const { formatSiteId } = useSiteOptions();
const { enabled: liveRefreshEnabled } = useDashboardLiveRefresh();

const RESOURCE_ROUTES: Record<string, string> = {
  sites: "/sites",
  rules: "/rules",
  blacklist: "/blacklist",
  whitelist: "/whitelist",
  exceptions: "/exceptions",
  ratelimits: "/ratelimit",
};

const MODE_CHART_COLORS: Record<string, string> = {
  observe: "#3b82f6",
  block: "#ef4444",
  captcha: "#f59e0b",
  js_challenge: "#a855f7",
  slide_captcha: "#06b6d4",
  unknown: "#94a3b8",
};

const SOURCE_CHART_COLORS = ["#2563eb", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316"];

const counts = reactive<OverviewCounts>({
  sites: { total: 0, enabled: 0 },
  rules: { total: 0, enabled: 0 },
  blacklist: { total: 0, enabled: 0 },
  whitelist: { total: 0, enabled: 0 },
  exceptions: { total: 0, enabled: 0 },
  ratelimits: { total: 0, enabled: 0 },
  certificates: { total: 0 },
});

const stats = reactive<any>({
  total: 0,
  blocked: 0,
  passed: 0,
  block_rate: 0,
  unique_ips: 0,
  unique_rules: 0,
  start: "",
  end: "",
  trend: [],
  top_rules: [],
  top_ips: [],
  top_domains: [],
  top_countries: [],
  top_methods: [],
  mode_split: [],
  source_split: [],
  log_type_split: [],
});

const summary = reactive<SummaryData>({});
const health = reactive<any>({
  database: "ok",
  redis: "ok",
  clickhouse: "ok",
  rule_sync: { status: "ok", version: null },
});
const feed = reactive<{ items: any[]; pending_ai_incidents: number }>({
  items: [],
  pending_ai_incidents: 0,
});
const intel = reactive<any>({ windows: [] });
const trafficSiteId = ref<number | undefined>(undefined);
const traffic = reactive<{ burst_active: boolean; windows: any[] }>({
  burst_active: false,
  windows: [],
});

const trafficCardTitle = computed(() =>
  trafficSiteId.value == null ? "实时全站流量" :"实时站点流量",
);

/** 异常检测仅展示有基线学习能力的窗口（排除 10s / 30s） */
const intelDisplayWindows = computed(() =>
  (intel.windows || []).filter((w: { window_sec: number }) => w.window_sec !== 10 && w.window_sec !== 30),
);

const feedLoading = ref(false);
const trendEl = ref<HTMLElement>();
const modeEl = ref<HTMLElement>();
const sourceEl = ref<HTMLElement>();
const countryEl = ref<HTMLElement>();
const logTypeEl = ref<HTMLElement>();

const charts: ECharts[] = [];
const LIVE_REFRESH_DELAY_MS = 8000;
let refreshTimer: ReturnType<typeof setTimeout> | null = null;
let liveRefreshRunning = false;
/** Epoch ms for rolling window end; numeric ref keeps live refresh label reactive. */
const dashboardWindowEndAt = ref(Date.now());
const liveClockTick = ref(0);
const timezoneTick = ref(0);

function enabledSub(item: CountPair) {
  if (item.enabled === undefined) return "";
  return `${item.enabled} 项已启用`;
}

const healthItems = computed(() => [
  { key: "database", label: "MySQL", status: health.database },
  { key: "redis", label: "Redis", status: health.redis },
  { key: "clickhouse", label: "ClickHouse", status: health.clickhouse },
]);

const resourceCards = computed(() => [
  { key: "sites", label: "防护站点", value: counts.sites.total, sub: enabledSub(counts.sites), color: "#2563eb", icon: ClusterOutlined },
  { key: "rules", label: "自定义规则", value: counts.rules.total, sub: enabledSub(counts.rules), color: "#7c3aed", icon: SafetyOutlined },
  { key: "blacklist", label: "黑名单", value: counts.blacklist.total, sub: enabledSub(counts.blacklist), color: "#dc2626", icon: StopOutlined },
  { key: "whitelist", label: "白名单", value: counts.whitelist.total, sub: enabledSub(counts.whitelist), color: "#16a34a", icon: CheckCircleOutlined },
  { key: "exceptions", label: "防护例外", value: counts.exceptions.total, sub: enabledSub(counts.exceptions), color: "#ea580c", icon: DisconnectOutlined },
  { key: "ratelimits", label: "速率防护", value: counts.ratelimits.total, sub: enabledSub(counts.ratelimits), color: "#0891b2", icon: ThunderboltOutlined },
]);

const securityCards = computed(() => [
  { key: "total", label: "请求命中", value: stats.total, sub: "WAF 检出并记录的请求", color: "#2563eb", valueColor: "#1d4ed8", icon: AlertOutlined, delta: summary.total_requests_delta_pct ?? undefined },
  { key: "blocked", label: "已拦截", value: stats.blocked, sub: `占比 ${stats.block_rate}%`, color: "#ef4444", valueColor: "#dc2626", icon: StopOutlined, delta: summary.blocked_delta_pct ?? undefined },
  { key: "passed", label: "已放行", value: stats.passed, sub: "观察 / 验证后放行", color: "#22c55e", valueColor: "#16a34a", icon: CheckCircleOutlined, delta: summary.passed_delta_pct ?? undefined },
  { key: "unique_ips", label: "独立 IP", value: stats.unique_ips, sub: "去重后的来源地址", color: "#8b5cf6", valueColor: "#7c3aed", icon: UserOutlined, delta: summary.unique_ips_delta_pct ?? undefined },
  { key: "rules", label: "命中规则", value: stats.unique_rules, sub: topRuleSummary(), color: "#7c3aed", valueColor: "#6d28d9", icon: SafetyOutlined },
  { key: "methods", label: "请求方法种类", value: stats.top_methods?.length || 0, sub: topMethodSummary(), color: "#0ea5e9", valueColor: "#0284c7", icon: FileTextOutlined },
]);

const statsWindowLabel = computed(() => {
  void timezoneTick.value;
  void liveClockTick.value;
  return formatClockTime(dashboardWindowEndAt.value);
});

const ruleCols = [
  { title: "规则", dataIndex: "name", ellipsis: true },
  { title: "命中", dataIndex: "count", width: 80, align: "right" as const },
];
const ipCols = [
  { title: "IP", dataIndex: "ip", ellipsis: true },
  { title: "命中", dataIndex: "count", width: 80, align: "right" as const },
];

function topMethodSummary() {
  const top = stats.top_methods?.[0];
  if (!top) return "暂无方法分布";
  return `最多: ${top.method} (${top.count})`;
}

function topRuleSummary() {
  const top = stats.top_rules?.[0];
  if (!top) return "暂无规则命中";
  return `最多: ${top.name} (${top.count})`;
}

function windowLabel(sec: number) {
  return trafficWindowLabels[sec] || `${sec} 秒`;
}

function formatIntelBaseline(value: number | null | undefined) {
  if (value == null) return "—";
  return Math.round(value);
}

function formatIntelDeviation(ratio: number) {
  const delta = ratio * 100 - 100;
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(0)}%`;
}

function progressColor(requests: number, threshold: number) {
  const ratio = threshold ? requests / threshold : 0;
  if (ratio >= 1) return "#ef4444";
  if (ratio >= 0.7) return "#f59e0b";
  return "#22c55e";
}

function formatTrendTime(value: string) {
  void timezoneTick.value;
  return formatDateTimeShort(value);
}

const FEED_PROTECTION_TYPES = new Set([
  "block",
  "js_challenge",
  "captcha",
  "slide_captcha",
]);

const FEED_TYPE_LABEL: Record<string, string> = {
  alert: "预警",
  block: "拦截",
  js_challenge: "JS 挑战",
  captcha: "数学验证",
  slide_captcha: "滑动验证",
};

function feedTone(item: { type?: string; severity?: string }) {
  if (item.type === "block" || item.severity === "danger") return "danger";
  if (item.type === "alert" || item.type === "captcha" || item.severity === "warning") {
    return "alert";
  }
  return "info";
}

function feedTypeLabel(type: string) {
  return FEED_TYPE_LABEL[type] || type;
}

function feedMeta(item: { site?: string | null; rule?: string | null; detail?: string | null }) {
  const parts: string[] = [];
  if (item.site) parts.push(`站点：${item.site}`);
  if (item.rule) parts.push(`规则：${item.rule}`);
  if (!parts.length && item.detail) return String(item.detail);
  return parts.join("  ");
}

function formatFeedTime(value: string) {
  void timezoneTick.value;
  return formatDateTime(value, "MM-DD HH:mm:ss");
}

function onResourceCardClick(key: string) {
  const path = RESOURCE_ROUTES[key];
  if (path) router.push(path);
}

function onSecurityCardClick(key: string) {
  switch (key) {
    case "total":
      goToLogs({ tab: "detail" });
      break;
    case "blocked":
      goToLogs({ tab: "detail", blocked: true });
      break;
    case "passed":
      goToLogs({ tab: "detail", blocked: false });
      break;
    case "unique_ips":
      goToLogs({ tab: "stats", dimension: "client_ip" });
      break;
    case "rules":
      goToLogs({ tab: "stats", dimension: "rule_id" });
      break;
    case "methods":
      goToLogs({ tab: "stats", dimension: "method" });
      break;
  }
}

function goLogs(filters: Parameters<typeof goToLogs>[0] = { tab: "detail" }) {
  goToLogs(filters);
}

function goAiGuard() {
  router.push("/ai-guard");
}

function onRuleClick(record: { id?: number; name: string }) {
  if (record.id) {
    goToLogs({ tab: "detail", rule_id: record.id });
    return;
  }
  goToLogs({ tab: "stats", dimension: "rule_id" });
}

function onIpClick(record: { ip: string }) {
  goToLogs({ tab: "detail", client_ip: record.ip });
}

function ruleTableRow(record: { id?: number; name: string }) {
  return {
    class: "clickable-row",
    onClick: () => onRuleClick(record),
  };
}

function ipTableRow(record: { ip: string }) {
  return {
    class: "clickable-row",
    onClick: () => onIpClick(record),
  };
}

function onFeedClick(item: { type: string; title?: string }) {
  if (item.type === "alert") {
    router.push("/alerts");
    return;
  }
  if (FEED_PROTECTION_TYPES.has(item.type)) {
    const ip = (item.title || "").trim();
    goToLogs({
      tab: "detail",
      blocked: true,
      mode: item.type,
      client_ip: ip && ip !== "未知 IP" ? ip : undefined,
    });
  }
}

type ChartKey = "trend" | "mode" | "source" | "country" | "logType";

const chartStore: Partial<Record<ChartKey, ECharts>> = {};

function chartMotion(silent: boolean): Pick<echarts.EChartsOption, "animation" | "animationDuration" | "animationDurationUpdate"> {
  return silent
    ? { animation: false, animationDuration: 0, animationDurationUpdate: 0 }
    : { animation: true, animationDuration: 300, animationDurationUpdate: 200 };
}

function upsertChart(
  key: ChartKey,
  el: HTMLElement | undefined,
  option: echarts.EChartsOption,
  onClick: ((params: { dataIndex: number }) => void) | undefined,
  silent: boolean,
) {
  if (!el) return;
  const motion = chartMotion(silent);
  const fullOption: echarts.EChartsOption = {
    ...option,
    ...motion,
    series: Array.isArray(option.series)
      ? option.series.map((s) => ({ ...s, ...motion }))
      : option.series,
  };

  let chart = chartStore[key];
  if (!chart || chart.isDisposed()) {
    chart = echarts.init(el, echartsThemeName(isDark.value));
    if (onClick) chart.on("click", onClick);
    chartStore[key] = chart;
    if (!charts.includes(chart)) charts.push(chart);
    chart.setOption(fullOption);
    return;
  }

  chart.setOption(fullOption, { notMerge: false, lazyUpdate: true });
}

function destroyCharts() {
  Object.values(chartStore).forEach((chart) => chart?.dispose());
  (Object.keys(chartStore) as ChartKey[]).forEach((key) => {
    delete chartStore[key];
  });
  charts.splice(0, charts.length);
}

function updateCharts(silent = false) {
  const times = stats.trend.map((t: any) => formatTrendTime(t.time));
  upsertChart(
    "trend",
    trendEl.value,
    {
      color: ["#ef4444", "#22c55e"],
      tooltip: { trigger: "axis" },
      legend: { data: ["已拦截", "已放行"], bottom: 0 },
      grid: { left: 12, right: 12, top: 24, bottom: 40, containLabel: true },
      xAxis: { type: "category", boundaryGap: false, data: times },
      yAxis: { type: "value", minInterval: 1 },
      series: [
        {
          name: "已拦截",
          type: "line",
          smooth: true,
          stack: "total",
          showSymbol: false,
          symbol: "none",
          areaStyle: lineAreaGradient("#ef4444"),
          data: stats.trend.map((t: any) => t.blocked ?? 0),
        },
        {
          name: "已放行",
          type: "line",
          smooth: true,
          stack: "total",
          showSymbol: false,
          symbol: "none",
          areaStyle: lineAreaGradient("#22c55e"),
          data: stats.trend.map((t: any) => t.passed ?? t.count ?? 0),
        },
      ],
    },
    () => goToLogs({ tab: "detail" }),
    silent,
  );

  upsertChart(
    "mode",
    modeEl.value,
    {
      tooltip: { trigger: "item" },
      legend: { bottom: 0, type: "scroll" },
      stateAnimation: { duration: 280, easing: "cubicOut" },
      series: [{
        type: "pie",
        radius: ["42%", "68%"],
        padAngle: 3,
        itemStyle: { borderRadius: 6, borderWidth: 2 },
        label: { formatter: "{b}\n{d}%" },
        emphasis: {
          scale: true,
          scaleSize: 8,
        },
        data: stats.mode_split.map((m: any) => ({
          name: m.label || m.mode,
          value: m.count,
          itemStyle: { color: MODE_CHART_COLORS[m.mode] || MODE_CHART_COLORS.unknown },
        })),
      }],
    },
    (params) => {
      const item = stats.mode_split[params.dataIndex];
      if (item?.mode) goToLogs({ tab: "detail", mode: item.mode });
    },
    silent,
  );

  upsertChart(
    "source",
    sourceEl.value,
    {
      color: SOURCE_CHART_COLORS,
      tooltip: { trigger: "axis" },
      grid: { left: 12, right: 12, top: 16, bottom: 8, containLabel: true },
      xAxis: { type: "category", data: stats.source_split.map((s: any) => s.label || s.source) },
      yAxis: { type: "value", minInterval: 1 },
      series: [{ type: "bar", barMaxWidth: 36, itemStyle: { borderRadius: [6, 6, 0, 0] }, data: stats.source_split.map((s: any) => s.count) }],
    },
    (params) => {
      const item = stats.source_split[params.dataIndex];
      if (item?.source) goToLogs({ tab: "detail", source: item.source });
    },
    silent,
  );

  const countries = [...stats.top_countries].reverse();
  upsertChart(
    "country",
    countryEl.value,
    {
      color: ["#2563eb"],
      tooltip: { trigger: "axis" },
      grid: { left: 12, right: 20, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: "value", minInterval: 1 },
      yAxis: { type: "category", data: countries.map((c: any) => c.label || c.country) },
      series: [{ type: "bar", barMaxWidth: 18, itemStyle: { borderRadius: [0, 6, 6, 0] }, data: countries.map((c: any) => c.count) }],
    },
    (params) => {
      const item = countries[params.dataIndex];
      const country = item?.country || item?.key;
      if (country) goToLogs({ tab: "detail", geo_country: country });
    },
    silent,
  );

  upsertChart(
    "logType",
    logTypeEl.value,
    {
      color: ["#0ea5e9", "#14b8a6", "#f59e0b"],
      tooltip: { trigger: "item" },
      legend: { bottom: 0 },
      series: [{
        type: "pie",
        radius: ["0%", "68%"],
        roseType: "radius",
        itemStyle: { borderRadius: 4 },
        label: { formatter: "{b}\n{c}" },
        data: stats.log_type_split.map((item: any) => ({ name: item.label || item.log_type, value: item.count })),
      }],
    },
    (params) => {
      const item = stats.log_type_split[params.dataIndex];
      const logType = item?.log_type || item?.key;
      if (logType) goToLogs({ tab: "detail", log_type: logType });
    },
    silent,
  );
}

function resizeCharts() {
  charts.forEach((chart) => chart.resize());
}

watch(isDark, async () => {
  destroyCharts();
  await nextTick();
  updateCharts(false);
});

async function loadTraffic() {
  const params = trafficSiteId.value != null ? { site_id: trafficSiteId.value } : {};
  const resp = await api.get("/api/v1/traffic/stats", params);
  traffic.burst_active = resp.data.burst_active || false;
  traffic.windows = resp.data.windows || resp.data.global?.windows || [];
}

async function loadIntel() {
  const params = trafficSiteId.value != null ? { site_id: trafficSiteId.value } : {};
  const resp = await api.get("/api/v1/traffic/intel/status", params);
  Object.assign(intel, resp.data);
}

function onTrafficSiteChange() {
  void refreshAll();
}

watch(trafficSiteId, () => {
  onTrafficSiteChange();
});

async function syncDashboardWindow() {
  dashboardWindowEndAt.value = Date.now();
  liveClockTick.value += 1;
  await nextTick();
}

async function refreshAll(silent = false) {
  await syncDashboardWindow();
  await Promise.allSettled([
    loadOverview(silent),
    loadSummary(),
    loadHealth(),
    loadFeed(silent),
    loadTraffic(),
    loadIntel(),
  ]);
  await syncDashboardWindow();
}

function scheduleLiveRefresh() {
  refreshTimer = setTimeout(async () => {
    refreshTimer = null;
    if (!liveRefreshRunning) return;
    await refreshAll(true);
    if (!liveRefreshRunning) return;
    scheduleLiveRefresh();
  }, LIVE_REFRESH_DELAY_MS);
}

function startLiveRefresh() {
  stopLiveRefresh();
  liveRefreshRunning = true;
  scheduleLiveRefresh();
}

function stopLiveRefresh() {
  liveRefreshRunning = false;
  if (!refreshTimer) return;
  clearTimeout(refreshTimer);
  refreshTimer = null;
}

watch(liveRefreshEnabled, (enabled) => {
  if (enabled) startLiveRefresh();
  else stopLiveRefresh();
});

watch(() => appSettings.timezone, async () => {
  timezoneTick.value += 1;
  await syncDashboardWindow();
  if (stats.trend.length) updateCharts(true);
});

async function loadOverview(silent = false) {
  const resp = await api.get("/api/v1/dashboard/overview");
  Object.assign(counts, resp.data.counts);
  Object.assign(stats, resp.data.last_24h);
  await nextTick();
  updateCharts(silent);
}

async function loadSummary() {
  const resp = await api.get("/api/v1/dashboard/summary");
  Object.assign(summary, resp.data);
}

async function loadHealth() {
  const resp = await api.get("/api/v1/dashboard/health");
  Object.assign(health, resp.data);
}

async function loadFeed(silent = false) {
  if (!silent) feedLoading.value = true;
  try {
    const resp = await api.get("/api/v1/dashboard/feed", { limit: 15 });
    feed.items = resp.data.items || [];
    feed.pending_ai_incidents = resp.data.pending_ai_incidents || 0;
  } finally {
    if (!silent) feedLoading.value = false;
  }
}

onMounted(async () => {
  if (!appSettings.loaded) {
    await appSettings.fetch();
  }
  timezoneTick.value += 1;
  await refreshAll();
  if (liveRefreshEnabled.value) startLiveRefresh();
  window.addEventListener("resize", resizeCharts);
});

onUnmounted(() => {
  stopLiveRefresh();
  destroyCharts();
  window.removeEventListener("resize", resizeCharts);
});
</script>

<style scoped>
.page-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 4px 0 8px;
  background: transparent;
}

.hero-main {
  min-width: 0;
}

.hero-heading {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--fs-radius-md);
  flex-shrink: 0;
  font-size: 22px;
  color: var(--fs-color-primary);
  background: var(--fs-color-primary);
  color: #fff;
}

.hero-text {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding-top: 2px;
}

.hero-title-row {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px 10px;
}

.hero-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--fs-text-primary);
  line-height: 1.2;
}

.hero-desc {
  color: var(--fs-text-secondary);
  font-size: 13px;
  line-height: 1.2;
}

.hero-health {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 14px;
}

.hero-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
  margin-left: auto;
  padding-top: 4px;
}

.hero-time {
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  color: var(--fs-text-secondary);
  line-height: 1;
}

.health-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--fs-text-muted);
}

.health-dot.ok {
  background: var(--fs-color-accent);
}

.health-dot.error,
.health-dot.stale {
  background: var(--fs-color-danger);
}

.health-text {
  color: var(--fs-text-secondary);
}

.health-ai-link {
  cursor: pointer;
  margin-inline-end: 0;
}

.panel-card-clickable {
  cursor: pointer;
  transition: box-shadow var(--fs-transition), transform var(--fs-transition);
}

.panel-card-clickable:hover {
  box-shadow: var(--fs-shadow-md);
}

.panel-title-link {
  cursor: pointer;
}

.panel-title-link:hover {
  color: var(--fs-color-primary);
}

:deep(.clickable-row) {
  cursor: pointer;
}

:deep(.clickable-row:hover td) {
  background: var(--fs-bg-muted) !important;
}

.panel-card {
  border-radius: var(--fs-radius-md);
  box-shadow: var(--fs-shadow-sm);
  height: 100%;
}

.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.traffic-site-filter {
  width: 150px !important;
}

.traffic-metrics-panel :deep(.ant-card-head) {
  padding: 0 16px;
}

.traffic-metrics-panel :deep(.ant-card-body) {
  padding: 12px 14px 14px;
}

.metric-window-card {
  height: 100%;
  min-width: 0;
  padding: 8px 10px;
  border-radius: var(--fs-radius-sm);
  background: var(--fs-bg-muted);
  border: 1px solid var(--fs-border);
}

.metric-window-label {
  font-size: 11px;
  line-height: 1.3;
  color: var(--fs-text-secondary);
}

.metric-window-value {
  margin-top: 2px;
  font-size: 22px;
  line-height: 1.25;
  font-weight: 700;
  color: var(--fs-text-primary);
}

.metric-window-meta {
  margin-left: 4px;
  font-size: 10px;
  font-weight: 500;
  color: var(--fs-text-muted);
  white-space: nowrap;
}

.metric-window-sub {
  margin-top: 8px;
  font-size: 10px;
  line-height: 1.35;
  color: var(--fs-text-muted);
}

.metric-window-progress {
  margin-top: 4px;
  margin-bottom: 0;
}

.metric-window-progress :deep(.ant-progress-inner) {
  height: 3px !important;
}

.intel-item.anomaly {
  border-color: var(--fs-color-warning);
  background: color-mix(in srgb, var(--fs-color-warning) 10%, var(--fs-bg-muted));
}

.intel-deviation {
  white-space: nowrap;
}

.intel-warmup {
  color: #f59e0b;
  white-space: nowrap;
}

.chart-box {
  height: 260px;
}

.chart-box-lg {
  height: 320px;
}

.feed-card :deep(.ant-card-body) {
  padding-top: 8px;
  padding-bottom: 12px;
}

.feed-list-body {
  max-height: 430px;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

.feed-timeline {
  list-style: none;
  margin: 0;
  padding: 4px 0 4px 2px;
}

.feed-timeline-item {
  --feed-tone: var(--fs-color-info);
  --feed-tone-bg: color-mix(in srgb, var(--fs-color-info) 12%, transparent);
  position: relative;
  display: flex;
  gap: 12px;
  padding: 12px 4px 12px 0;
  cursor: pointer;
  transition: background var(--fs-transition);
}

.feed-timeline-item:last-child {
  border-bottom: none;
}

.feed-timeline-item:hover {
  background: color-mix(in srgb, var(--fs-bg-muted) 80%, transparent);
}

.feed-timeline-item--alert {
  --feed-tone: var(--fs-color-info);
  --feed-tone-bg: color-mix(in srgb, var(--fs-color-info) 12%, transparent);
}

.feed-timeline-item--danger {
  --feed-tone: var(--fs-color-danger);
  --feed-tone-bg: color-mix(in srgb, var(--fs-color-danger) 12%, transparent);
}

.feed-timeline-item--info {
  --feed-tone: var(--fs-color-primary);
  --feed-tone-bg: color-mix(in srgb, var(--fs-color-primary) 12%, transparent);
}

.feed-timeline-item::before {
  content: "";
  position: absolute;
  left: 5px;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--fs-border);
}

.feed-timeline-item:first-child::before {
  top: 18px;
}

.feed-timeline-item:last-child::before {
  bottom: calc(100% - 18px);
}

.feed-timeline-dot {
  position: relative;
  z-index: 1;
  flex: 0 0 11px;
  width: 11px;
  height: 11px;
  margin-top: 5px;
  border-radius: 50%;
  background: var(--feed-tone);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--feed-tone) 16%, var(--fs-bg-surface));
}

.feed-timeline-main {
  flex: 1;
  min-width: 0;
}

.feed-timeline-top {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.feed-timeline-tag {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  color: var(--feed-tone);
  background: var(--feed-tone-bg);
}

.feed-timeline-title {
  flex: 1;
  min-width: 0;
  color: var(--fs-text-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.45;
  word-break: break-word;
}

.feed-timeline-time {
  flex-shrink: 0;
  margin-left: 4px;
  color: var(--fs-text-muted);
  font-size: 12px;
  line-height: 20px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.feed-timeline-meta {
  margin-top: 4px;
  padding-left: 0;
  color: var(--fs-text-muted);
  font-size: 12px;
  line-height: 1.5;
  word-break: break-word;
}

@media (max-width: 767px) {
  .feed-timeline-top {
    flex-wrap: wrap;
  }

  .feed-timeline-time {
    width: 100%;
    margin-left: 0;
    padding-left: 0;
  }
}

@media (max-width: 767px) {
  .page-hero {
    padding: 0 0 4px;
  }

  .hero-title {
    font-size: 18px;
  }

  .hero-icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }

  .hero-actions {
    margin-left: 0;
    align-items: flex-start;
  }

  .chart-box,
  .chart-box-lg {
    height: 240px;
  }
}
</style>
