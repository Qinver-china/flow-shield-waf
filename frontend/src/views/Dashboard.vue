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
                  {{ item.label }} {{ healthStatusSuffix(item.status) }}
                </span>
              </div>
              <a-tag v-if="feed.pending_ai_incidents > 0" color="orange" class="health-ai-link" @click="goAiGuard">
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
        <stat-card clickable :label="item.label" :value="item.value" :sub="item.sub" :color="item.color"
          :icon="item.icon" @click="onResourceCardClick(item.key)" />
      </a-col>
    </a-row>

    <div class="dashboard-scope-bar">
      <h3 class="fs-section-title"><safety-outlined /> 近 24 小时安全态势</h3>
      <div class="dashboard-scope-filters">
        <site-single-select v-model:value="trafficSiteId" :show-search="false" class="traffic-site-filter" />
      </div>
    </div>
    <a-row :gutter="[12, 12]">
      <a-col v-for="item in securityCards" :key="item.key" :xs="12" :sm="8" :md="8" :xl="4">
        <stat-card large clickable :label="item.label" :value="item.value" :sub="item.sub" :color="item.color"
          :value-color="item.valueColor" :icon="item.icon" :delta="item.delta" @click="onSecurityCardClick(item.key)" />
      </a-col>
    </a-row>
    <a-row :gutter="[12, 12]">
      <a-col :xs="24" :lg="14" :xl="15">
        <a-card class="panel-card traffic-live-panel" :bordered="false">
          <template #title>
            <div class="traffic-live-title">
              <span class="panel-title"><thunderbolt-outlined /> 实时请求量</span>
              <span class="traffic-live-badge" :class="liveRefreshEnabled ? 'is-live' : 'is-paused'">
                <span class="traffic-live-badge__dot" />
                {{ liveRefreshEnabled ? "实时更新" : "已暂停刷新" }}
              </span>
              <a-tag v-if="traffic.burst_active" color="orange">自动取证中</a-tag>
            </div>
          </template>

          <a-empty v-if="!liveTrafficWindows.length" description="暂无数据" />
          <template v-else>
            <div class="traffic-live-hero">
              <div class="traffic-live-hero__metric">
                <div class="traffic-live-hero__label">{{ liveTrafficDay.label }}</div>
                <div class="traffic-live-hero__value">{{ formatTrafficCount(liveTrafficDay.requests) }}</div>
                <div class="traffic-live-hero__meta">
                  <span>平均 {{ formatQps(liveTrafficDay.qps) }} QPS</span>
                  <span class="traffic-live-hero__origin">
                    回源 <b>{{ formatTrafficCount(liveTrafficDay.origin_requests) }}</b>
                    · {{ formatQps(liveTrafficDay.origin_qps) }} QPS
                  </span>
                  <span v-if="liveTrafficDay.deviation_ratio != null && !liveTrafficDay.baseline_warmup"
                    class="traffic-live-hero__delta" :class="liveTrafficCardClass(liveTrafficDay)">
                    {{ formatIntelDeviation(liveTrafficDay.deviation_ratio) }}
                  </span>
                </div>
              </div>
              <div class="traffic-live-hero__divider" />
              <div class="traffic-live-hero__status" :class="`is-${liveTrafficOverall.tone}`">
                <div class="traffic-live-hero__status-title">
                  <component :is="liveTrafficOverall.icon" />
                  <span>{{ liveTrafficOverall.title }}</span>
                </div>
                <div class="traffic-live-hero__status-desc">{{ liveTrafficOverall.desc }}</div>
              </div>
            </div>

            <div class="traffic-live-grid">
              <div v-for="w in liveTrafficWindowCards" :key="w.window_sec" class="traffic-live-card"
                :class="liveTrafficCardClass(w)">
                <div class="traffic-live-card__head">
                  <span class="traffic-live-card__label">{{ w.label }}</span>
                </div>
                <div class="traffic-live-card__value">{{ formatTrafficCount(w.requests) }}</div>
                <div class="traffic-live-card__qps">{{ formatQps(w.qps) }} QPS</div>
                <div class="traffic-live-card__origin">
                  <span>回源请求 <b>{{ formatTrafficCount(w.origin_requests) }}</b></span>
                  <span>回源QPS <b>{{ formatQps(w.origin_qps) }}</b></span>
                </div>
                <a-tooltip v-if="liveTrafficHasBaselineWindow(w)" :title="liveTrafficBaselineTip(w)"
                  overlay-class-name="baseline-status-tooltip" :mouse-enter-delay="0.25">
                  <div class="traffic-live-card__status">
                    <component :is="liveTrafficStatusIcon(w)" class="traffic-live-card__status-icon" />
                    <span class="traffic-live-card__baseline-text">
                      <template v-if="w.baseline_avg != null">
                        <span>{{ formatTrafficCount(w.baseline_avg) }}</span>
                        <span v-if="w.deviation_ratio != null" class="traffic-live-card__ratio">
                          {{ formatIntelDeviation(w.deviation_ratio) }}
                        </span>
                      </template>
                      <template v-else>暂无基线</template>
                    </span>
                  </div>
                </a-tooltip>
                <div v-else class="traffic-live-card__status is-baseline-ghost">
                  <component :is="liveTrafficStatusIcon(w)" class="traffic-live-card__status-icon" />
                  <span class="traffic-live-card__baseline-text">暂无基线</span>
                </div>
                <a-progress :percent="liveTrafficBarPercent(w)" size="small" :stroke-color="liveTrafficBarColor(w)"
                  :show-info="false" class="traffic-live-card__bar" />
              </div>
            </div>
          </template>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="10" :xl="9">
        <a-card class="panel-card load-card" :bordered="false">
          <template #title>
            <div class="load-card-title">
              <span class="panel-title"><cloud-server-outlined /> CPU负载</span>
              <span class="load-status-badge" :class="`is-${loadOverall.tone}`">
                <span class="load-status-badge__dot" />
                {{ loadOverall.title }}
              </span>
            </div>
          </template>
          <div class="load-body">
            <div class="load-main">
              <div ref="loadCpuEl" class="load-gauge-box" />
              <div class="load-main-foot" :class="`is-${loadOverall.tone}`">
                <component :is="loadOverall.icon" />
                <span>{{ loadOverall.hint }}</span>
              </div>
            </div>
            <div class="load-side">
              <div v-for="(item, idx) in loadMetricCards" :key="item.key" class="load-side-card"
                :class="[item.kind === 'host' ? 'is-host' : 'is-container', `is-${cpuTone(item.pct)}`]">
                <div class="load-side-card__label">{{ item.label }}</div>
                <div class="load-side-ring" :ref="(el) => setLoadMiniEl(idx, el)" />
                <div class="load-side-card__value">
                  {{ item.value }}<span v-if="item.pct != null" class="load-side-card__unit">%</span>
                </div>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[12, 12]">
      <a-col :span="24">
        <a-card class="panel-card traffic-timeline-panel" :bordered="false">
          <template #title>
            <span class="panel-title"><line-chart-outlined />24H请求趋势</span>
          </template>
          <template #extra>
            <a-select v-model:value="trafficTimelineBucket" class="traffic-timeline-bucket"
              :options="trafficTimelineBucketOptions" />
          </template>
          <div ref="trafficTimelineEl" class="chart-box chart-box-lg" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[12, 12]">
      <a-col :span="24">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title panel-title-link" @click.stop="goLogs()">
              <line-chart-outlined /> 24H命中趋势
            </span>
          </template>
          <template #extra>
            <a-select v-model:value="trafficTimelineBucket" class="traffic-timeline-bucket"
              :options="trafficTimelineBucketOptions" />
          </template>
          <div ref="trendEl" class="chart-box chart-box-lg" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[12, 12]">
      <a-col :xs="24" :md="8">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><pie-chart-outlined /> 防护方式分布</span>
          </template>
          <div ref="modeEl" class="chart-box chart-box-lg" />
        </a-card>
      </a-col>
      <a-col :xs="24" :md="8">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><bar-chart-outlined /> 防护来源</span>
          </template>
          <div ref="sourceEl" class="chart-box chart-box-lg" />
        </a-card>
      </a-col>
      <a-col :xs="24" :md="8">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><global-outlined /> 拦截来源国家 Top</span>
          </template>
          <div ref="countryEl" class="chart-box chart-box-lg" />
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="[12, 12]">
      <a-col :xs="24" :lg="6">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><alert-outlined /> Top 命中规则</span>
          </template>
          <a-table class="feed-list-body" :columns="ruleCols" :data-source="stats.top_rules" :pagination="false"
            :row-key="(record: { id?: number; name: string }) => String(record.id ?? record.name)" size="small" bordered
            :show-sorter-tooltip="false"
            :scroll="{ x: 180 }" :custom-row="ruleTableRow" />
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="6">
        <a-card class="panel-card" :bordered="false">
          <template #title>
            <span class="panel-title"><aim-outlined /> Top 攻击 IP</span>
          </template>
          <a-table class="feed-list-body" :columns="ipCols" :data-source="stats.top_ips" :pagination="false"
            row-key="ip" size="small" bordered :scroll="{ x: 180 }" :show-sorter-tooltip="false" :custom-row="ipTableRow" />
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
                <li v-for="item in feed.items" :key="item.id" class="feed-timeline-item"
                  :class="`feed-timeline-item--${feedTone(item)}`" @click="onFeedClick(item)">
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
  ClockCircleOutlined,
  CloudServerOutlined,
  ClusterOutlined,
  DashboardOutlined,
  DisconnectOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  GlobalOutlined,
  LineChartOutlined,
  MinusCircleOutlined,
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
import { echartsThemeName, prepareChartOption } from "@/composables/useEchartsTheme";
import { useAppSettingsStore } from "@/stores/appSettings";
import { useThemeStore } from "@/stores/theme";
import dayjs from "dayjs";
import { formatClockTime, formatDateTime, formatDateTimeShort, getAppTimezone, parseUtc } from "@/utils/datetime";
import { lineAreaGradient } from "@/utils/lineAreaGradient";
import { baselineTone } from "@/utils/baselineTone";
import { trafficWindowLabels, buildTrendModeSeries, modeChartColor, trendModeValue } from "@/views/logs/constants";

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

/** Sequential palette for ranked bar charts (source / country). */
const RANK_BAR_COLORS = [
  "#2563eb",
  "#ef4444",
  "#8b5cf6",
  "#14b8a6",
  "#f97316",
  "#0ea5e9",
  "#eab308",
  "#ec4899",
  "#22c55e",
  "#6366f1",
];

function rankBarColor(index: number): string {
  return RANK_BAR_COLORS[index % RANK_BAR_COLORS.length];
}
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
  trend_modes: [],
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
  engine: "ok",
  worker: "ok",
  rule_sync: { status: "ok", version: null },
});
const feed = reactive<{ items: any[]; pending_ai_incidents: number }>({
  items: [],
  pending_ai_incidents: 0,
});
const intel = reactive<any>({ windows: [] });
const trafficSiteId = ref<number | undefined>(undefined);
const traffic = reactive<{
  burst_active: boolean;
  windows: any[];
  site_count: number;
}>({
  burst_active: false,
  windows: [],
  site_count: 0,
});

const trafficTimelineBucket = ref(1800);
const trafficTimelineBucketOptions = [
  { value: 60, label: "1 分钟" },
  { value: 300, label: "5 分钟" },
  { value: 600, label: "10 分钟" },
  { value: 1800, label: "30 分钟" },
  { value: 3600, label: "1 小时" },
];

const TREND_GRANULARITY_BY_BUCKET: Record<number, string> = {
  60: "1m",
  300: "5m",
  600: "10m",
  1800: "30m",
  3600: "1h",
};

function dashboardSiteParams(): Record<string, number> {
  if (trafficSiteId.value == null) return {};
  return { site_id: trafficSiteId.value };
}

function dashboardTrendGranularity(): string {
  return TREND_GRANULARITY_BY_BUCKET[trafficTimelineBucket.value] || "10m";
}

function dashboardQueryParams(extra: Record<string, string | number> = {}) {
  return { ...dashboardSiteParams(), ...extra };
}
const trafficTimeline = reactive<{ points: Array<{ ts: number; requests: number; origin_requests: number }> }>({
  points: [],
});
const trafficTimelineEl = ref<HTMLElement>();

const systemMetrics = reactive({
  window_sec: 60,
  window_label: "1 分钟",
  container_cpu_pct: null as number | null,
  host_cpu_pct: null as number | null,
  windows: [] as Array<{
    sec: number;
    label: string;
    container_cpu_pct: number | null;
    host_cpu_pct: number | null;
    samples?: number | null;
    ready?: boolean | null;
  }>,
  cpu_cores: null as number | null,
  source: null as string | null,
  updated_at: null as number | null,
  available: false,
});

function formatCpuPct(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return Number(value).toFixed(digits);
}

function cpuTone(pct: number | null | undefined): "ok" | "warn" | "danger" | "neutral" {
  if (pct == null || Number.isNaN(Number(pct))) return "neutral";
  const n = Number(pct);
  if (n >= 85) return "danger";
  if (n >= 60) return "warn";
  return "ok";
}

/** 右侧：容器 5m/30m + 宿主机 5m/30m */
const loadMetricCards = computed(() => {
  const windows = systemMetrics.windows || [];
  const bySec = (sec: number) => windows.find((w) => w.sec === sec);
  const w5 = bySec(300);
  const w30 = bySec(1800);
  return [
    {
      key: "c-300",
      kind: "container" as const,
      label: "容器 · 5 分钟",
      value: formatCpuPct(w5?.container_cpu_pct ?? null, 1),
      pct: w5?.container_cpu_pct ?? null,
    },
    {
      key: "c-1800",
      kind: "container" as const,
      label: "容器 · 30 分钟",
      value: formatCpuPct(w30?.container_cpu_pct ?? null, 1),
      pct: w30?.container_cpu_pct ?? null,
    },
    {
      key: "h-300",
      kind: "host" as const,
      label: "宿主机 · 5 分钟",
      value: formatCpuPct(w5?.host_cpu_pct ?? null, 1),
      pct: w5?.host_cpu_pct ?? null,
    },
    {
      key: "h-1800",
      kind: "host" as const,
      label: "宿主机 · 30 分钟",
      value: formatCpuPct(w30?.host_cpu_pct ?? null, 1),
      pct: w30?.host_cpu_pct ?? null,
    },
  ];
});

const loadOverall = computed(() => {
  const pct = systemMetrics.container_cpu_pct;
  const tone = cpuTone(pct);
  if (tone === "danger") {
    return {
      tone,
      title: "负载过高",
      hint: "容器CPU负载高于 85%",
      icon: ExclamationCircleOutlined,
    };
  }
  if (tone === "warn") {
    return {
      tone,
      title: "负载偏高",
      hint: "容器CPU负载较高",
      icon: ExclamationCircleOutlined,
    };
  }
  if (tone === "neutral") {
    return {
      tone,
      title: "采样中",
      hint: "需满 1 分钟样本后显示均值",
      icon: MinusCircleOutlined,
    };
  }
  return {
    tone: "ok" as const,
    title: "运行正常",
    hint: "负载稳定",
    icon: CheckCircleOutlined,
  };
});
/** 合并实时流量 + 基线：10s～24h */
const liveTrafficWindows = computed(() => {
  const intelBySec = new Map<number, any>();
  for (const w of intel.windows || []) {
    const sec = Number(w.window_sec);
    if (Number.isFinite(sec)) intelBySec.set(sec, w);
  }

  const fromTraffic = (traffic.windows || []).map((w: any) => {
    const sec = Number(w.sec);
    const intelW = intelBySec.get(sec);
    const requests = Number(w.requests || 0);
    const originRequests = Number(w.origin_requests || 0);
    const baselineAvg =
      intelW?.baseline_avg != null ? Number(intelW.baseline_avg) : null;
    // QPS = 窗口内请求合计 ÷ 窗口秒数（全部站点即各站请求之和 ÷ 时间）。
    const qps = sec > 0 ? requests / sec : 0;
    const originQps = sec > 0 ? originRequests / sec : 0;
    return {
      window_sec: sec,
      label: windowLabel(sec),
      requests,
      qps,
      origin_requests: originRequests,
      origin_qps: originQps,
      threshold: w.threshold != null ? Number(w.threshold) : null,
      baseline_avg: baselineAvg,
      baseline_warmup: Boolean(intelW?.baseline_warmup),
      deviation_ratio:
        intelW?.deviation_ratio != null
          ? Number(intelW.deviation_ratio)
          : baselineAvg && baselineAvg > 0
            ? requests / baselineAvg
            : null,
    };
  });

  if (fromTraffic.length) return fromTraffic;

  return (intel.windows || []).map((w: any) => {
    const sec = Number(w.window_sec);
    const requests = Number(w.current_requests || 0);
    return {
      window_sec: sec,
      label: w.label || windowLabel(sec),
      requests,
      qps: requests / Math.max(sec, 1),
      origin_requests: 0,
      origin_qps: 0,
      threshold: null as number | null,
      baseline_avg: w.baseline_avg != null ? Number(w.baseline_avg) : null,
      baseline_warmup: Boolean(w.baseline_warmup),
      deviation_ratio:
        w.deviation_ratio != null ? Number(w.deviation_ratio) : null,
    };
  });
});

/** 底部子卡片：10s～60m（24h 放在顶部摘要） */
const liveTrafficWindowCards = computed(() =>
  liveTrafficWindows.value.filter((w) => w.window_sec !== 86400),
);

const liveTrafficDay = computed(() => {
  const day = liveTrafficWindows.value.find((w) => w.window_sec === 86400);
  if (day) return day;
  return {
    window_sec: 86400,
    label: windowLabel(86400),
    requests: 0,
    qps: 0,
    origin_requests: 0,
    origin_qps: 0,
    threshold: null as number | null,
    baseline_avg: null as number | null,
    baseline_warmup: false,
    deviation_ratio: null as number | null,
  };
});

const liveTrafficOverall = computed(() => {
  const scored = liveTrafficWindows.value.filter(
    (w) => w.baseline_avg != null || w.threshold != null,
  );
  const tones = scored.map((w) => baselineTone(w.deviation_ratio));
  if (tones.includes("danger")) {
    return {
      tone: "danger" as const,
      title: "流量偏高",
      desc: "部分时间窗请求量明显高于基线，建议结合日志排查。",
      icon: ExclamationCircleOutlined,
    };
  }
  if (tones.includes("warn")) {
    return {
      tone: "warn" as const,
      title: "需关注",
      desc: "部分时间窗高于基线，请留意是否持续上升。",
      icon: ExclamationCircleOutlined,
    };
  }
  if (!scored.length) {
    return {
      tone: "neutral" as const,
      title: "暂无基线",
      desc: "尚无可用基线；下方展示实时窗口请求量。",
      icon: MinusCircleOutlined,
    };
  }
  if (scored.some((w) => w.baseline_warmup)) {
    return {
      tone: "ok" as const,
      title: "流量正常",
      desc: "基线仍在学习中，当前请求量相对初步基线未见异常偏高。",
      icon: SafetyCertificateOutlined,
    };
  }
  return {
    tone: "ok" as const,
    title: "流量正常",
    desc: "当前请求量在基线范围内波动，未检测到异常。",
    icon: SafetyCertificateOutlined,
  };
}); const feedLoading = ref(false);
const trendEl = ref<HTMLElement>();
const modeEl = ref<HTMLElement>();
const loadCpuEl = ref<HTMLElement>();
/** Non-reactive: function refs must not write reactive state (causes render loops). */
const loadMiniEls: (HTMLElement | null)[] = [];

function setLoadMiniEl(idx: number, el: unknown) {
  const node = el instanceof HTMLElement ? el : null;
  if (loadMiniEls[idx] === node) return;
  loadMiniEls[idx] = node;
}
const sourceEl = ref<HTMLElement>();
const countryEl = ref<HTMLElement>();

const charts: ECharts[] = [];
const LIVE_REFRESH_DELAY_MS = 8000;
let refreshTimer: ReturnType<typeof setTimeout> | null = null;
let liveRefreshRunning = false;
let refreshSeq = 0;
/** Epoch ms for rolling window end; numeric ref keeps live refresh label reactive. */
const dashboardWindowEndAt = ref(Date.now());
const liveClockTick = ref(0);
const timezoneTick = ref(0);

function enabledSub(item: CountPair) {
  if (item.enabled === undefined) return "";
  return `${item.enabled} 项已启用`;
}

function healthStatusSuffix(status: string) {
  if (status === "ok") return "正常";
  if (status === "stale") return "滞后";
  return "异常";
}

const healthItems = computed(() => [
  { key: "database", label: "SQLite", status: health.database },
  { key: "redis", label: "Redis", status: health.redis },
  { key: "clickhouse", label: "ClickHouse", status: health.clickhouse },
  { key: "engine", label: "WAF 引擎", status: health.engine },
  { key: "worker", label: "后台 Worker", status: health.worker },
  { key: "rule_sync", label: "规则同步", status: health.rule_sync?.status || "error" },
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
  { key: "rules", label: "命中规则", value: stats.unique_rules, sub: topRuleSummary(), color: "#ed673e", valueColor: "#f5663a", icon: SafetyOutlined },
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

function formatQps(value: number | null | undefined) {
  return Number(value || 0).toFixed(1);
}

function formatTrafficCount(value: number | null | undefined) {
  const n = Math.round(Number(value || 0));
  return Number.isFinite(n) ? n.toLocaleString("zh-CN") : "0";
}

function formatTrafficTimelineTooltipTime(tsMs: number, bucketSec: number): string {
  void timezoneTick.value;
  const start = dayjs(tsMs).tz(getAppTimezone());
  const fmt = "YYYY-MM-DD HH:mm";
  if (bucketSec <= 60) {
    return start.format(fmt);
  }
  const end = start.add(bucketSec, "second");
  if (start.format("YYYY-MM-DD") === end.format("YYYY-MM-DD")) {
    return `${start.format(fmt)} ~ ${end.format("HH:mm")}`;
  }
  return `${start.format(fmt)} ~ ${end.format(fmt)}`;
}

function formatIntelDeviation(ratio: number) {
  const delta = ratio * 100 - 100;
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(0)}%`;
}

type LiveTrafficWindow = {
  window_sec: number;
  label?: string;
  requests: number;
  qps?: number;
  threshold?: number | null;
  baseline_avg?: number | null;
  baseline_warmup?: boolean;
  deviation_ratio?: number | null;
};

function liveTrafficHasBaselineWindow(w: LiveTrafficWindow) {
  // 与后端 TRAFFIC_BASELINE_WINDOWS_SEC 对齐：10s / 30s 不学基线
  return w.window_sec !== 10 && w.window_sec !== 30;
}

function liveTrafficBaselineTip(w: LiveTrafficWindow) {
  if (!liveTrafficHasBaselineWindow(w)) return "";
  if (w.baseline_avg == null) return "暂无可用基线";
  const parts = [`基线 ${formatTrafficCount(w.baseline_avg)}`];
  if (w.deviation_ratio != null) {
    parts.push(`相对 ${formatIntelDeviation(w.deviation_ratio)}`);
  }
  parts.push(w.baseline_warmup ? "学习中" : "已稳定");
  return parts.join(" · ");
}

function liveTrafficCardClass(w: LiveTrafficWindow) {
  if (w.baseline_avg == null && (w.threshold == null || w.threshold <= 0)) {
    return "is-neutral";
  }
  // 学习中同样按请求量/基线比值着色
  const tone = baselineTone(w.deviation_ratio);
  if (tone === "warn") return "is-warn";
  if (tone === "danger") return "is-danger";
  return "is-ok";
}

function liveTrafficStatusIcon(w: LiveTrafficWindow) {
  if (w.baseline_avg == null) return MinusCircleOutlined;
  if (w.baseline_warmup) return ClockCircleOutlined;
  const tone = baselineTone(w.deviation_ratio);
  if (tone === "danger" || tone === "warn") return ExclamationCircleOutlined;
  return CheckCircleOutlined;
}

/** 10s/30s 无基线：按 QPS 映射进度条。
 * 单站：0.1→10%，10→100%；全部站点：满分 = 10 × 站点数。
 */
function liveTrafficQpsBarScaleMax() {
  if (trafficSiteId.value != null) return 10;
  const n = Math.max(1, Number(traffic.site_count) || 1);
  return 10 * n;
}

function liveTrafficQpsBarPercent(qps: number | null | undefined) {
  const q = Math.round(Number(qps || 0) * 10) / 10;
  if (q <= 0) return 0;
  const scaleMax = liveTrafficQpsBarScaleMax();
  const floor = 0.1;
  const pct = 10 + ((q - floor) / Math.max(scaleMax - floor, 0.1)) * 90;
  return Math.min(100, Math.max(0, Math.round(pct)));
}

/** 有基线：相对 -100%（0×）≈10%，3× 基线满格；10s/30s 按 QPS；否则阈值/占位。 */
function liveTrafficBarPercent(w: LiveTrafficWindow) {
  if (!liveTrafficHasBaselineWindow(w)) {
    return liveTrafficQpsBarPercent(w.qps);
  }
  if (w.baseline_avg != null && w.baseline_avg > 0) {
    const ratio = w.requests / w.baseline_avg;
    return Math.min(100, Math.max(0, Math.round(10 + ratio * 30)));
  }
  if (w.threshold != null && w.threshold > 0) {
    return Math.min(100, Math.round((w.requests / w.threshold) * 100));
  }
  return w.requests > 0 ? 28 : 0;
}

function liveTrafficBarColor(w: LiveTrafficWindow) {
  if (!liveTrafficHasBaselineWindow(w)) {
    const pct = liveTrafficQpsBarPercent(w.qps);
    if (pct > 70) return "#ef4444";
    if (pct > 40) return "#f59e0b";
    return "#22c55e";
  }
  if (w.baseline_avg != null) {
    const tone = baselineTone(w.deviation_ratio);
    if (tone === "danger") return "#ef4444";
    if (tone === "warn") return "#f59e0b";
    return "#22c55e";
  }
  if (w.threshold != null && w.threshold > 0) {
    const ratio = w.requests / w.threshold;
    if (ratio >= 1) return "#ef4444";
    if (ratio >= 0.7) return "#f59e0b";
    return "#22c55e";
  }
  return "#94a3b8";
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
      goLogs({ tab: "detail" });
      break;
    case "blocked":
      goLogs({ tab: "detail", blocked: true });
      break;
    case "passed":
      goLogs({ tab: "detail", blocked: false });
      break;
    case "unique_ips":
      goLogs({ tab: "stats", dimension: "client_ip" });
      break;
    case "rules":
      goLogs({ tab: "stats", dimension: "rule_id" });
      break;
    case "methods":
      goLogs({ tab: "stats", dimension: "method" });
      break;
  }
}

function goLogs(filters: Parameters<typeof goToLogs>[0] = { tab: "detail" }) {
  goToLogs({
    ...filters,
    ...dashboardSiteParams(),
  });
}

function goAiGuard() {
  router.push("/ai-guard");
}

function onRuleClick(record: { id?: number; name: string }) {
  if (record.id) {
    goLogs({ tab: "detail", rule_id: record.id });
    return;
  }
  goLogs({ tab: "stats", dimension: "rule_id" });
}

function onIpClick(record: { ip: string }) {
  goLogs({ tab: "detail", client_ip: record.ip });
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
    goLogs({
      tab: "detail",
      blocked: true,
      mode: item.type,
      client_ip: ip && ip !== "未知 IP" ? ip : undefined,
    });
  }
}

type ChartKey =
  | "trend"
  | "trafficTimeline"
  | "mode"
  | "loadCpu"
  | "loadMini0"
  | "loadMini1"
  | "loadMini2"
  | "loadMini3"
  | "source"
  | "country";

const TREND_CHART_GROUP = "dashboard-trend-link";

function trendPointTimeMs(time: string): number {
  void timezoneTick.value;
  if (!time) return 0;
  const parsed = parseUtc(time);
  return parsed.isValid() ? parsed.valueOf() : 0;
}

const TREND_WINDOW_HOURS = 24;

function trendWindowBoundsSec(): { start: number; end: number } {
  void liveClockTick.value;
  const endSec = Math.floor(dashboardWindowEndAt.value / 1000);
  const endMinute = endSec - (endSec % 60);
  const startMinute = endMinute - (TREND_WINDOW_HOURS * 60 - 1) * 60;
  return { start: startMinute, end: endMinute };
}

function iterTrendBucketStartsSec(bucketSec: number, endSec: number, startSec: number): number[] {
  const endMinute = endSec - (endSec % 60);
  const startMinute = startSec - (startSec % 60);
  const firstBucket = Math.floor(startMinute / bucketSec) * bucketSec;
  const buckets: number[] = [];
  for (let bucket = firstBucket; bucket <= endMinute; bucket += bucketSec) {
    buckets.push(bucket);
  }
  return buckets;
}

function trendTimeAxisBounds(): { min: number; max: number } {
  const { start, end } = trendWindowBoundsSec();
  return { min: start * 1000, max: end * 1000 };
}

function filledTrafficTimelinePoints(): Array<{ ts: number; requests: number; origin_requests: number }> {
  const bucketSec = trafficTimelineBucket.value;
  const { start, end } = trendWindowBoundsSec();
  const byTs = new Map<number, { ts: number; requests: number; origin_requests: number }>();
  for (const point of trafficTimeline.points || []) {
    byTs.set(point.ts, point);
  }
  return iterTrendBucketStartsSec(bucketSec, end, start).map((ts) => (
    byTs.get(ts) ?? { ts, requests: 0, origin_requests: 0 }
  ));
}

function filledHitTrendRows(): any[] {
  const bucketSec = trafficTimelineBucket.value;
  const { start, end } = trendWindowBoundsSec();
  const byBucket = new Map<number, any>();
  for (const row of stats.trend || []) {
    if (!row.time) continue;
    const aligned = Math.floor(parseUtc(row.time).unix() / bucketSec) * bucketSec;
    byBucket.set(aligned, row);
  }
  return iterTrendBucketStartsSec(bucketSec, end, start).map((bucketTs) => (
    byBucket.get(bucketTs) ?? {
      time: new Date(bucketTs * 1000).toISOString().slice(0, 19).replace("T", " "),
      count: 0,
      total: 0,
      by_mode: {},
    }
  ));
}

function syncTrendChartLinkage() {
  const trafficChart = chartStore.trafficTimeline;
  const hitChart = chartStore.trend;
  if (!trafficChart || !hitChart || trafficChart.isDisposed() || hitChart.isDisposed()) return;
  trafficChart.group = TREND_CHART_GROUP;
  hitChart.group = TREND_CHART_GROUP;
  echarts.connect(TREND_CHART_GROUP);
}

function disconnectTrendChartLinkage() {
  echarts.disconnect(TREND_CHART_GROUP);
}

const chartStore: Partial<Record<ChartKey, ECharts>> = {};

function chartMotion(silent: boolean): Pick<echarts.EChartsOption, "animation" | "animationDuration" | "animationDurationUpdate"> {
  // Keep animation enabled so pie emphasis scale still eases on hover.
  // Silent refresh only short-circuits data enter/update durations.
  return silent
    ? { animation: true, animationDuration: 0, animationDurationUpdate: 0 }
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
  const fullOption: echarts.EChartsOption = prepareChartOption({
    ...option,
    ...motion,
    series: Array.isArray(option.series)
      ? option.series.map((s) => ({ ...s, ...motion }))
      : option.series,
  }, isDark.value);

  let chart = chartStore[key];
  if (!chart || chart.isDisposed()) {
    chart = echarts.init(el, echartsThemeName(isDark.value));
    if (onClick) chart.on("click", onClick);
    chartStore[key] = chart;
    if (!charts.includes(chart)) charts.push(chart);
    chart.setOption(fullOption);
    return;
  }

  chart.setOption(fullOption, {
    notMerge: key === "loadCpu" || key.startsWith("loadMini"),
    lazyUpdate: true,
  });
}

function destroyCharts() {
  disconnectTrendChartLinkage();
  Object.values(chartStore).forEach((chart) => chart?.dispose());
  (Object.keys(chartStore) as ChartKey[]).forEach((key) => {
    delete chartStore[key];
  });
  charts.splice(0, charts.length);
}

function loadCpuRingColor(pct: number): string {
  if (pct >= 85) return "#ef4444";
  if (pct >= 60) return "#f59e0b";
  return "#22c55e";
}

function cpuRingTrackColor(): string {
  return isDark.value ? "rgba(148,163,184,0.16)" : "rgba(148,163,184,0.2)";
}

/** 仪表盘拱形半环（无底边，类似汽车仪表）。 */
function buildCpuArcOption(opts: {
  pct: number | null;
  centerTitle?: string;
  /** Two-line subtitle under the percentage (main gauge). */
  centerTitleLines?: { primary: string; secondary: string };
  valueFontSize?: number;
  unitFontSize?: number;
  titleFontSize?: number;
  /** Arc span; default ~240° for main gauge. */
  startAngle?: number;
  endAngle?: number;
  radius?: string;
  center?: [string, string];
  lineWidth?: number;
  showLabels?: boolean;
}): echarts.EChartsOption {
  const hasValue = opts.pct != null && !Number.isNaN(Number(opts.pct));
  const pct = hasValue ? Math.max(0, Math.min(100, Number(opts.pct))) : 0;
  const color = hasValue ? loadCpuRingColor(pct) : "#94a3b8";
  const track = cpuRingTrackColor();
  const valueFill = isDark.value ? "#f8fafc" : "#0f172a";
  const mutedFill = isDark.value ? "#94a3b8" : "#64748b";
  const secondaryFill = isDark.value ? "#cbd5e1" : "#475569";
  const valueSize = opts.valueFontSize ?? 30;
  const unitSize = opts.unitFontSize ?? 14;
  const titleSize = opts.titleFontSize ?? 12;
  const title = (opts.centerTitle || "").trim();
  const titleLines = opts.centerTitleLines;
  const showLabels = opts.showLabels !== false;
  const lineWidth = opts.lineWidth ?? 12;
  const useTitleLines = Boolean(titleLines?.primary);

  const detailFormatter = () => {
    const valuePart = hasValue ? `{v|${pct.toFixed(1)}}{u|%}` : "{e|—}";
    if (!showLabels) return valuePart;
    if (useTitleLines && titleLines) {
      // ECharts gauge rich 的 padding 对换行间距几乎无效，用空行 + height 拉开间距
      return `${valuePart}\n{gap1| }\n{t|${titleLines.primary}}\n{gap2| }\n{s|${titleLines.secondary}}`;
    }
    return valuePart;
  };

  return {
    tooltip: { show: false },
    series: [
      {
        type: "gauge",
        center: opts.center || ["50%", "70%"],
        radius: opts.radius || "83%",
        startAngle: opts.startAngle ?? 210,
        endAngle: opts.endAngle ?? -30,
        min: 0,
        max: 100,
        splitNumber: 0,
        silent: true,
        axisLine: {
          roundCap: true,
          lineStyle: {
            width: lineWidth,
            color: [[1, track]],
          },
        },
        progress: {
          show: true,
          roundCap: true,
          width: lineWidth,
          itemStyle: { color },
        },
        pointer: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        anchor: { show: false },
        title: {
          show: showLabels && !useTitleLines,
          offsetCenter: [0, "18%"],
          color: mutedFill,
          fontSize: titleSize,
          fontWeight: 500,
        },
        detail: {
          show: showLabels,
          valueAnimation: true,
          // 整块文案相对圆心下移约 20px
          offsetCenter: useTitleLines ? [0, 20] : [0, "-12%"],
          formatter: detailFormatter,
          rich: {
            v: {
              fontSize: valueSize,
              fontWeight: 700,
              color: valueFill,
              lineHeight: valueSize + 4,
              padding: [0, 1, 0, 0],
            },
            u: {
              fontSize: unitSize,
              fontWeight: 600,
              color: valueFill,
              lineHeight: valueSize + 4,
              padding: [11, 0, 0, 1],
            },
            e: {
              fontSize: valueSize,
              fontWeight: 700,
              color: valueFill,
              lineHeight: valueSize + 4,
            },
            gap1: {
              fontSize: 1,
              lineHeight: 14,
              height: 14,
            },
            gap2: {
              fontSize: 1,
              lineHeight: 2,
              height: 2,
            },
            t: {
              fontSize: titleSize,
              fontWeight: 500,
              color: secondaryFill,
              lineHeight: titleSize + 4,
              align: "center",
            },
            s: {
              fontSize: Math.max(10, titleSize - 1),
              fontWeight: 400,
              color: mutedFill,
              lineHeight: titleSize + 4,
              align: "center",
            },
          },
        },
        data: [
          {
            value: hasValue ? pct : 0,
            name: showLabels && !useTitleLines
              ? (hasValue ? title || "容器 CPU" : "暂无数据")
              : "",
          },
        ],
      },
    ],
  };
}

function updateLoadChart(silent = false) {
  upsertChart(
    "loadCpu",
    loadCpuEl.value,
    buildCpuArcOption({
      pct: systemMetrics.container_cpu_pct,
      centerTitleLines: {
        primary: "容器 CPU 负载",
        secondary: "一分钟均值",
      },
      valueFontSize: 36,
      unitFontSize: 15,
      titleFontSize: 12,
      // 容器内上下居中；环略放大，百分比更突出
      center: ["50%", "52%"],
      radius: "99%",
      lineWidth: 14,
    }),
    undefined,
    silent,
  );

  const miniKeys: ChartKey[] = ["loadMini0", "loadMini1", "loadMini2", "loadMini3"];
  loadMetricCards.value.forEach((item, idx) => {
    const key = miniKeys[idx];
    if (!key) return;
    upsertChart(
      key,
      loadMiniEls[idx] || undefined,
      buildCpuArcOption({
        pct: item.pct,
        startAngle: 180,
        endAngle: 0,
        radius: "100%",
        center: ["50%", "72%"],
        lineWidth: 6,
        showLabels: false,
      }),
      undefined,
      silent,
    );
  });
}

function updateTrafficTimelineChart(silent = false) {
  const bucketSec = trafficTimelineBucket.value;
  const axisBounds = trendTimeAxisBounds();
  const points = filledTrafficTimelinePoints();
  const dataRequests = points.map((p) => [p.ts * 1000, p.requests]);
  const dataOrigins = points.map((p) => [p.ts * 1000, p.origin_requests]);
  upsertChart(
    "trafficTimeline",
    trafficTimelineEl.value,
    {
      color: ["#2563eb", "#14b8a6"],
      tooltip: {
        trigger: "axis",
        formatter(params: any) {
          const rows = Array.isArray(params) ? params : [params];
          if (!rows.length) return "";
          const tsMs = Number(rows[0].value[0]);
          const time = formatTrafficTimelineTooltipTime(tsMs, bucketSec);
          const lines = rows.map((row: any) => {
            const count = Number(row.value[1] || 0);
            const qps = count / bucketSec;
            return `${row.marker}${row.seriesName}: ${formatTrafficCount(count)} · ${formatQps(qps)} QPS`;
          });
          return `${time}<br/>${lines.join("<br/>")}`;
        },
      },
      axisPointer: { type: "line", snap: true },
      legend: { data: ["请求量", "回源请求量"], bottom: 0 },
      grid: { left: 12, right: 12, top: 24, bottom: 40, containLabel: true },
      xAxis: { type: "time", boundaryGap: false, min: axisBounds.min, max: axisBounds.max },
      yAxis: { type: "value", minInterval: 1 },
      series: [
        {
          name: "请求量",
          type: "line",
          smooth: true,
          showSymbol: false,
          itemStyle: { color: "#2563eb" },
          areaStyle: lineAreaGradient("#2563eb"),
          data: dataRequests,
        },
        {
          name: "回源请求量",
          type: "line",
          smooth: true,
          showSymbol: false,
          itemStyle: { color: "#14b8a6" },
          areaStyle: lineAreaGradient("#14b8a6"),
          data: dataOrigins,
        },
      ],
    },
    undefined,
    silent,
  );
  syncTrendChartLinkage();
}

function updateCharts(silent = false) {
  const hitTrendRows = filledHitTrendRows();
  const seriesDefs = buildTrendModeSeries(hitTrendRows, stats.trend_modes);
  const bucketSec = trafficTimelineBucket.value;
  const axisBounds = trendTimeAxisBounds();
  upsertChart(
    "trend",
    trendEl.value,
    {
      color: seriesDefs.map((s) => s.color),
      tooltip: {
        trigger: "axis",
        formatter(params: any) {
          const rows = Array.isArray(params) ? params : [params];
          if (!rows.length) return "";
          const tsMs = Number(rows[0].value[0]);
          const time = formatTrafficTimelineTooltipTime(tsMs, bucketSec);
          const lines = rows.map((row: any) => {
            const count = Number(row.value[1] || 0);
            return `${row.marker}${row.seriesName}: ${formatTrafficCount(count)}`;
          });
          return `${time}<br/>${lines.join("<br/>")}`;
        },
      },
      axisPointer: { type: "line", snap: true },
      legend: { data: seriesDefs.map((s) => s.name), bottom: 0 },
      grid: { left: 12, right: 12, top: 24, bottom: 40, containLabel: true },
      xAxis: { type: "time", boundaryGap: false, min: axisBounds.min, max: axisBounds.max },
      yAxis: { type: "value", minInterval: 1 },
      series: seriesDefs.map((s) => ({
        name: s.name,
        type: "line",
        smooth: true,
        showSymbol: false,
        symbol: "none",
        itemStyle: { color: s.color },
        areaStyle: lineAreaGradient(s.color),
        data: hitTrendRows.map((t: any) => [trendPointTimeMs(t.time), trendModeValue(t, s.key)]),
      })),
    },
    () => goToLogs({ tab: "detail" }),
    silent,
  );
  syncTrendChartLinkage();

  upsertChart(
    "mode",
    modeEl.value,
    {
      tooltip: { trigger: "item" },
      legend: { bottom: 0, type: "scroll" },
      series: [{
        type: "pie",
        radius: ["42%", "68%"],
        padAngle: 3,
        itemStyle: { borderRadius: 6, borderWidth: 0 },
        label: { formatter: "{b}\n{d}%" },
        // Hover scale transition (must live on series; root-level is ignored).
        stateAnimation: { duration: 320, easing: "cubicOut" },
        emphasis: {
          scale: true,
          scaleSize: 8,
        },
        data: stats.mode_split.map((m: any) => ({
          name: m.label || m.mode,
          value: m.count,
          itemStyle: { color: modeChartColor[m.mode] || modeChartColor.unknown },
        })),
      }],
    },
    (params) => {
      const item = stats.mode_split[params.dataIndex];
      if (item?.mode) goToLogs({ tab: "detail", mode: item.mode });
    },
    silent,
  );

  updateLoadChart(silent);

  upsertChart(
    "source",
    sourceEl.value,
    {
      tooltip: { trigger: "axis" },
      grid: { left: 12, right: 12, top: 16, bottom: 8, containLabel: true },
      xAxis: { type: "category", data: stats.source_split.map((s: any) => s.label || s.source) },
      yAxis: { type: "value", minInterval: 1 },
      series: [{
        type: "bar",
        barMaxWidth: 36,
        itemStyle: { borderRadius: [6, 6, 0, 0] },
        data: stats.source_split.map((s: any, i: number) => ({
          value: s.count,
          itemStyle: { color: rankBarColor(i) },
        })),
      }],
    },
    (params) => {
      const item = stats.source_split[params.dataIndex];
      if (item?.source) goToLogs({ tab: "detail", source: item.source });
    },
    silent,
  );

  // Rank colors by original order (Top1 = first color), then reverse for y-axis display.
  const countryBars = stats.top_countries.map((c: any, i: number) => ({
    raw: c,
    name: c.label || c.country,
    value: c.count,
    itemStyle: { color: rankBarColor(i) },
  })).reverse();
  upsertChart(
    "country",
    countryEl.value,
    {
      tooltip: { trigger: "axis" },
      grid: { left: 12, right: 20, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: "value", minInterval: 1 },
      yAxis: { type: "category", data: countryBars.map((c) => c.name) },
      series: [{
        type: "bar",
        barMaxWidth: 18,
        itemStyle: { borderRadius: [0, 6, 6, 0] },
        data: countryBars.map((c) => ({
          value: c.value,
          itemStyle: c.itemStyle,
        })),
      }],
    },
    (params) => {
      const item = countryBars[params.dataIndex]?.raw;
      const country = item?.country || item?.key;
      if (country) goToLogs({ tab: "detail", geo_country: country });
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
  updateTrafficTimelineChart(false);
});

async function loadTrafficTimeline(silent = false) {
  const resp = await api.get("/api/v1/traffic/timeline", dashboardQueryParams({
    hours: 24,
    bucket_sec: trafficTimelineBucket.value,
  }));
  trafficTimeline.points = resp.data.points || [];
  await nextTick();
  updateTrafficTimelineChart(silent);
}

async function loadTraffic() {
  const resp = await api.get("/api/v1/traffic/stats", dashboardSiteParams());
  traffic.burst_active = resp.data.burst_active || false;
  traffic.windows = resp.data.windows || resp.data.global?.windows || [];
  traffic.site_count = Number(resp.data.site_count || (resp.data.sites || []).length || 0);
}

async function loadIntel() {
  const resp = await api.get("/api/v1/traffic/intel/status", dashboardSiteParams());
  Object.assign(intel, resp.data);
}

async function loadSystemMetrics(silent = false) {
  const resp = await api.get("/api/v1/dashboard/system-metrics");
  Object.assign(systemMetrics, resp.data || {});
  await nextTick();
  await nextTick();
  updateLoadChart(silent);
}

function onTrafficSiteChange() {
  void refreshAll();
}

watch(trafficSiteId, () => {
  onTrafficSiteChange();
});

watch(trafficTimelineBucket, () => {
  void Promise.allSettled([loadTrafficTimeline(true), loadOverview(true)]);
});

async function syncDashboardWindow() {
  dashboardWindowEndAt.value = Date.now();
  liveClockTick.value += 1;
  await nextTick();
}

async function refreshAll(silent = false) {
  const seq = ++refreshSeq;
  await syncDashboardWindow();
  if (seq !== refreshSeq) return;
  await Promise.allSettled([
    loadOverview(silent),
    loadSummary(),
    loadHealth(),
    loadFeed(silent),
    loadTraffic(),
    loadTrafficTimeline(silent),
    loadIntel(),
    loadSystemMetrics(silent),
  ]);
  if (seq !== refreshSeq) return;
  await syncDashboardWindow();
}

function scheduleLiveRefresh() {
  refreshTimer = setTimeout(async () => {
    refreshTimer = null;
    if (!liveRefreshRunning) return;
    if (typeof document !== "undefined" && document.hidden) {
      scheduleLiveRefresh();
      return;
    }
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

function onVisibilityChange() {
  if (!liveRefreshRunning || !liveRefreshEnabled.value) return;
  if (!document.hidden) {
    void refreshAll(true);
  }
}

watch(liveRefreshEnabled, (enabled) => {
  if (enabled) startLiveRefresh();
  else stopLiveRefresh();
});

watch(() => appSettings.timezone, async () => {
  timezoneTick.value += 1;
  await syncDashboardWindow();
  if (stats.trend.length) updateCharts(true);
  if (trafficTimeline.points.length) updateTrafficTimelineChart(true);
});

async function loadOverview(silent = false) {
  const resp = await api.get("/api/v1/dashboard/overview", dashboardQueryParams({
    trend_granularity: dashboardTrendGranularity(),
  }));
  Object.assign(counts, resp.data.counts);
  Object.assign(stats, resp.data.last_24h);
  await nextTick();
  updateCharts(silent);
}

async function loadSummary() {
  const resp = await api.get("/api/v1/dashboard/summary", dashboardSiteParams());
  Object.assign(summary, resp.data);
}

async function loadHealth() {
  const resp = await api.get("/api/v1/dashboard/health");
  Object.assign(health, resp.data);
}

async function loadFeed(silent = false) {
  if (!silent) feedLoading.value = true;
  try {
    const resp = await api.get("/api/v1/dashboard/feed", dashboardQueryParams({ limit: 15 }));
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
  document.addEventListener("visibilitychange", onVisibilityChange);
});

onUnmounted(() => {
  stopLiveRefresh();
  destroyCharts();
  window.removeEventListener("resize", resizeCharts);
  document.removeEventListener("visibilitychange", onVisibilityChange);
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
  font-size: 12px;
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
  box-shadow: none;
  height: 100%;
  border: 1px solid var(--fs-border);
}

.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.dashboard-scope-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.dashboard-scope-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.traffic-timeline-bucket {
  width: 96px;
}

.traffic-live-panel :deep(.ant-card-head) {
  padding: 0 18px;
  min-height: 52px;
}

.traffic-live-panel :deep(.ant-card-body) {
  padding: 4px 18px 14px;
}

.traffic-live-title {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.traffic-live-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  line-height: 1.4;
}

.traffic-live-badge.is-live {
  color: #15803d;
  background: color-mix(in srgb, var(--fs-color-accent) 14%, transparent);
}

.traffic-live-badge.is-paused {
  color: var(--fs-text-muted);
  background: var(--fs-bg-muted);
}

.traffic-live-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.traffic-live-badge.is-live .traffic-live-badge__dot {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--fs-color-accent) 28%, transparent);
  animation: traffic-live-pulse 1.6s ease-out infinite;
}

@keyframes traffic-live-pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--fs-color-accent) 40%, transparent);
  }

  70% {
    box-shadow: 0 0 0 6px transparent;
  }

  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}

.traffic-live-hero {
  display: flex;
  padding: 14px 0;
  gap: 20px;
}

.traffic-live-hero__metric {
  flex: 1;
  min-width: 0;
}

.traffic-live-hero__label {
  font-size: 12px;
  color: var(--fs-text-secondary);
}

.traffic-live-hero__value {
  margin-top: 4px;
  font-size: 34px;
  line-height: 1.1;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--fs-text-primary);
  font-variant-numeric: tabular-nums;
}

.traffic-live-hero__meta {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--fs-text-muted);
}

.traffic-live-hero__delta {
  font-weight: 600;
}

.traffic-live-hero__delta.is-ok {
  color: var(--fs-color-primary);
}

.traffic-live-hero__delta.is-warn {
  color: var(--fs-color-warning);
}

.traffic-live-hero__delta.is-danger {
  color: var(--fs-color-danger);
}

.traffic-live-hero__divider {
  width: 1px;
  align-self: stretch;
  background: color-mix(in srgb, var(--fs-border) 40%, transparent);
  flex: none;
}

.traffic-live-hero__status {
  flex: 2;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 20px;
}

.traffic-live-hero__status-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 700;
}

.traffic-live-hero__status.is-ok .traffic-live-hero__status-title {
  color: var(--fs-color-accent);
}

.traffic-live-hero__status.is-warn .traffic-live-hero__status-title {
  color: var(--fs-color-warning);
}

.traffic-live-hero__status.is-danger .traffic-live-hero__status-title {
  color: var(--fs-color-danger);
}

.traffic-live-hero__status.is-neutral .traffic-live-hero__status-title {
  color: var(--fs-text-secondary);
}

.traffic-live-hero__status-desc {
  font-size: 12px;
  line-height: 1.5;
  color: var(--fs-text-secondary);
}

.traffic-live-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

@media (min-width: 768px) {
  .traffic-live-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}


@media (min-width: 1200px) {
  .traffic-live-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}


.traffic-live-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 12px;
  border-radius: var(--fs-radius-sm);
  background: var(--fs-bg-muted);
  border: 1px solid var(--fs-border);
  transition: border-color var(--fs-transition), background var(--fs-transition), box-shadow var(--fs-transition);
}


.traffic-live-card.is-warn {
  border-color: color-mix(in srgb, var(--fs-color-warning) 40%, var(--fs-border));
  background: color-mix(in srgb, var(--fs-color-warning) 5%, var(--fs-bg-muted));
}

.traffic-live-card.is-danger {
  border-color: color-mix(in srgb, var(--fs-color-danger) 40%, var(--fs-border));
  background: color-mix(in srgb, var(--fs-color-danger) 5%, var(--fs-bg-muted));
}

.traffic-live-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.traffic-live-card__label {
  font-size: 12px;
  color: var(--fs-text-secondary);
}

.traffic-live-card__value {
  margin-top: 6px;
  font-size: 24px;
  line-height: 1.15;
  font-weight: 700;
  color: var(--fs-text-primary);
  font-variant-numeric: tabular-nums;
}

.traffic-live-card__qps {
  margin-top: 2px;
  font-size: 12px;
  color: var(--fs-text-muted);
}

.traffic-live-card__origin {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
  line-height: 1.35;
  color: var(--fs-text-secondary);
  font-variant-numeric: tabular-nums;
}

.traffic-live-card__origin span:last-child {
  color: var(--fs-text-muted);
}

.traffic-live-hero__origin {
  color: var(--fs-text-secondary);
}

.traffic-live-card__status {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: nowrap;
  color: var(--fs-text-secondary);
  min-height: 18px;
  min-width: 0;
}

.traffic-live-card__status.is-baseline-ghost {
  opacity: 0;
  pointer-events: none;
  user-select: none;
}

.traffic-live-card__status-icon {
  font-size: 13px;
  flex: none;
}

.traffic-live-card__baseline-text {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
  min-width: 0;
  overflow: hidden;
  font-size: 11px;
  line-height: 1.3;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.traffic-live-card.is-ok .traffic-live-card__status {
  color: #15803d;
}

.traffic-live-card.is-warn .traffic-live-card__status {
  color: #b45309;
}

.traffic-live-card.is-danger .traffic-live-card__status {
  color: #b91c1c;
}

.traffic-live-card.is-neutral .traffic-live-card__status {
  color: var(--fs-text-muted);
}

.traffic-live-card__ratio {
  font-weight: 600;
  opacity: 0.9;
}

.traffic-live-card__bar {
  margin-top: auto;
  padding-top: 0;
  margin-bottom: -8px;
}

.traffic-live-card__bar :deep(.ant-progress-inner) {
  height: 6px !important;
  background: color-mix(in srgb, var(--fs-border) 70%, transparent) !important;
}

.traffic-live-footer {
  margin-top: 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--fs-text-muted);
}

.traffic-site-filter {
    width: 180px !important;
  }


@media (max-width: 767px) {
  .traffic-live-hero {
    gap: 16px;
  }

  .traffic-live-hero__value {
    font-size: 28px;
  }

  .traffic-live-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.chart-box {
  height: 260px;
}

.chart-box-lg {
  height: 320px;
}

.load-card :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
}

.load-card-title {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.load-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
}

.load-status-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.load-status-badge.is-ok {
  color: #15803d;
  background: color-mix(in srgb, var(--fs-color-accent) 14%, transparent);
}

.load-status-badge.is-warn {
  color: #b45309;
  background: color-mix(in srgb, var(--fs-color-warning) 14%, transparent);
}

.load-status-badge.is-danger {
  color: #b91c1c;
  background: color-mix(in srgb, var(--fs-color-danger) 12%, transparent);
}

.load-status-badge.is-neutral {
  color: var(--fs-text-muted);
  background: var(--fs-bg-muted);
}

.load-window-tag {
  font-size: 12px;
  color: var(--fs-text-secondary);
}

.load-body {
  display: flex;
  gap: 20px;
  align-items: center;
  flex: 1;
  min-height: 0;
  justify-content: space-around;
}

.load-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  min-height: 0;
}

.load-gauge-box {
  width: 240px;
  height: 192px;
  flex: none;
  overflow: visible;
}

.load-main-foot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 2px;
  font-size: 12px;
  font-weight: 600;
}

.load-main-foot.is-ok {
  color: #15803d;
}

.load-main-foot.is-warn {
  color: #b45309;
}

.load-main-foot.is-danger {
  color: #b91c1c;
}

.load-main-foot.is-neutral {
  color: var(--fs-text-muted);
}

.load-side {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  border: 1px solid var(--fs-border);
  border-radius: var(--fs-radius-sm);
  overflow: hidden;
  min-height: 168px;
  background: var(--fs-bg-surface);
}

.load-side-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-evenly;
  gap: 4px;
  padding: 10px 8px;
  min-width: 0;
  min-height: 0;
  background: var(--fs-bg-surface);
}

.load-side-card:nth-child(1),
.load-side-card:nth-child(2) {
  border-bottom: 1px solid var(--fs-border);
}

.load-side-card:nth-child(1),
.load-side-card:nth-child(3) {
  border-right: 1px solid var(--fs-border);
}

.load-side-card__label {
  font-size: 12px;
  line-height: 1.3;
  color: var(--fs-text-secondary);
  text-align: center;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.load-side-card.is-host .load-side-card__label {
  color: #2563eb;
}

.load-side-ring {
  width: 56px;
  height: 36px;
  flex: none;
}

.load-side-card__value {
  font-size: 20px;
  line-height: 1.1;
  font-weight: 700;
  color: var(--fs-text-primary);
  font-variant-numeric: tabular-nums;
  text-align: center;
}

.load-side-card__unit {
  margin-left: 1px;
  font-size: 12px;
  font-weight: 600;
}

.load-side-card.is-warn .load-side-card__value {
  color: #b45309;
}

.load-side-card.is-danger .load-side-card__value {
  color: #b91c1c;
}

.load-side-card.is-neutral .load-side-card__value {
  color: var(--fs-text-muted);
}

.feed-card :deep(.ant-card-body) {
  padding-top: 8px;
  padding-bottom: 12px;
}

.feed-list-body {
  max-height: 430px;
  overflow-y: auto;
  overflow-x: hidden;
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
  color: var(--fs-text-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.45;
  word-break: break-word;
  flex-shrink: 0;
  display: inline-flex;
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

@media (max-width: 1200px) {

  .load-body {
    flex-direction: column;
  }


}

@media (max-width: 992px) {

  .load-body {
    flex-direction: row;
  }
}

@media (max-width: 767px) {
  .feed-timeline-top {
    flex-wrap: wrap;
  }
}

@media (max-width: 767px) {
  .page-hero {
    padding: 0 0 4px;
  }

  .dashboard-page .panel-card :deep(.ant-card-head) {
    padding-left: 16px;
    padding-right: 16px;
  }

  .dashboard-page .panel-card :deep(.ant-card-body) {
    padding: 16px;
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

  .load-card :deep(.ant-card-body) {
    min-height: 0;
  }

  .load-body {
    flex-direction: column;
  }

  .load-side {
    min-height: 200px;
  }
}
</style>
