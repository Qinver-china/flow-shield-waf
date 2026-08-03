<template>
  <div class="log-stats-tab">
    <div class="stats-body">
      <log-stats-dimension-picker
        v-if="isMobileLayout"
        :model-value="dimension"
        trigger-variant="card"
        @change="selectDimension"
      />
      <a-card
        v-else
        size="small"
        class="dimension-panel"
        title="统计维度"
      >
        <div class="dimension-scroll">
          <section
            v-for="group in statsDimensionGroups"
            :key="group.label"
            class="dimension-group"
          >
            <div class="dimension-group-title">{{ group.label }}</div>
            <div class="dimension-grid">
              <button
                v-for="item in group.items"
                :key="item.key"
                type="button"
                class="dimension-btn"
                :class="{ active: dimension === item.key }"
                :title="item.desc"
                @click="selectDimension(item.key)"
              >
                {{ item.label }}
              </button>
            </div>
          </section>
        </div>
      </a-card>

      <div class="result-column">
        <a-row :gutter="12" class="summary-row">
          <a-col :span="8">
            <a-card size="small"><a-statistic title="命中总数" :value="overview.total" /></a-card>
          </a-col>
          <a-col :span="8">
            <a-card size="small">
              <a-statistic title="已拦截" :value="overview.blocked" :value-style="{ color: '#ef4444' }" />
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card size="small">
              <a-statistic title="已放行" :value="overview.passed" :value-style="{ color: '#22c55e' }" />
            </a-card>
          </a-col>
        </a-row>

        <a-card size="small" class="result-panel">
        <template #title>
          <span>{{ currentDimension?.label || "统计结果" }}</span>
          <span v-if="currentDimension?.desc" class="panel-desc">{{ currentDimension.desc }}</span>
        </template>

        <div class="chart-block">
          <div class="chart-block-header">
            <div class="chart-block-title">命中时间趋势</div>
            <a-dropdown :trigger="['click']" placement="bottomRight">
              <button type="button" class="granularity-trigger" @click.prevent>
                {{ trendGranularityLabel }}
                <down-outlined />
              </button>
              <template #overlay>
                <a-menu
                  class="granularity-menu"
                  :selected-keys="[trendGranularity]"
                  @click="onGranularitySelect"
                >
                  <a-menu-item v-for="item in trendGranularityOptions" :key="item.key">
                    {{ item.label }}
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
          <div class="chart-content">
            <div v-if="chartLoading" class="stats-chart chart-loading">
              <a-spin />
            </div>
            <a-empty
              v-else-if="!overview.trend.length"
              class="chart-empty"
              description="当前时间范围内暂无命中日志"
            />
            <div v-else ref="trendChartEl" class="stats-chart" />
          </div>
        </div>

        <a-table
          :columns="tableColumns"
          :data-source="groupItems"
          :loading="groupLoading"
          :pagination="tablePagination"
          size="small"
          row-key="key"
          class="stats-table"
          bordered
          @change="onTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'label'">
              <log-dimension-action-cell
                :label="record.label"
                :dimension="dimension"
                :item-key="record.key"
                :filter-state="filterState"
                @drill-down="emit('drill-down', buildDrillDown(record))"
              />
            </template>
            <template v-else-if="column.key === 'percent'">
              {{ percentOf(record.count) }}
            </template>
          </template>
        </a-table>
        </a-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, type LocationQuery } from "vue-router";
import { DownOutlined } from "@ant-design/icons-vue";
import * as echarts from "echarts";
import type { ECharts } from "echarts";
import { storeToRefs } from "pinia";
import { echartsThemeName, prepareChartOption } from "@/composables/useEchartsTheme";
import { useThemeStore } from "@/stores/theme";
import { api } from "@/api";
import { useResponsivePagination } from "@/composables/useResponsivePagination";
import { formatDateTime } from "@/utils/datetime";
import { lineAreaGradient } from "@/utils/lineAreaGradient";
import {
  localizeStatsItems,
  resolveAutoTrendGranularity,
  statsDimensionGroups,
  statsDimensions,
  trendGranularityOptions,
  buildTrendModeSeries,
  trendModeValue,
  type StatsDimension,
  type TrendGranularity,
} from "./constants";
import LogDimensionActionCell from "./LogDimensionActionCell.vue";
import LogStatsDimensionPicker from "./LogStatsDimensionPicker.vue";
import { useBreakpoint } from "@/composables/useBreakpoint";
import { useSiteOptions } from "@/composables/useSiteOptions";
import type { LogFilterState } from "./useLogFilterState";

export interface LogDrillDownFilter {
  dimension: StatsDimension;
  key: string;
  label: string;
  start: string;
  end: string;
}

const props = defineProps<{
  filterState: LogFilterState;
  active: boolean;
}>();

const emit = defineEmits<{ "drill-down": [LogDrillDownFilter] }>();

const { formatSiteId } = useSiteOptions();
const { paginationSize } = useResponsivePagination();
const { width } = useBreakpoint();
const route = useRoute();
const { isDark } = storeToRefs(useThemeStore());

const isMobileLayout = computed(() => width.value <= 900);

function queryValue(query: LocationQuery, key: string) {
  const value = query[key];
  if (Array.isArray(value)) return value[0];
  return value;
}

function resolveDimension(query: LocationQuery): StatsDimension {
  const next = queryValue(query, "dimension") as StatsDimension | undefined;
  if (next && statsDimensions.some((item) => item.key === next)) {
    return next;
  }
  return "rule_id";
}

const overview = reactive({
  total: 0,
  blocked: 0,
  passed: 0,
  trend: [] as any[],
  trend_modes: [] as Array<{ mode: string; label?: string }>,
});
const groupLoading = ref(false);
const chartLoading = ref(false);
const groupItems = ref<any[]>([]);
const groupTotal = ref(0);
const groupItemTotal = ref(0);
const groupPage = ref(1);
const groupPageSize = ref(20);
const dimension = ref<StatsDimension>(resolveDimension(route.query));
const trendChartEl = ref<HTMLElement>();
const initialized = ref(false);
const trendGranularity = ref<TrendGranularity>("10m");

let trendChart: ECharts | null = null;
let trendObserver: ResizeObserver | null = null;

const currentDimension = computed(() => statsDimensions.find((d) => d.key === dimension.value));
const trendGranularityLabel = computed(
  () => trendGranularityOptions.find((item) => item.key === trendGranularity.value)?.label || "颗粒度",
);

const tableColumns = computed(() => [
  {
    title: currentDimension.value?.label || "维度值",
    key: "label",
    dataIndex: "label",
    ellipsis: true,
  },
  { title: "数量", dataIndex: "count", width: 90 },
  { title: "占比", key: "percent", width: 80 },
]);

const tablePagination = computed(() => ({
  current: groupPage.value,
  pageSize: groupPageSize.value,
  total: groupItemTotal.value,
  size: paginationSize.value,
  showTotal: (total: number) => `共 ${total} 项`,
  showSizeChanger: true,
  pageSizeOptions: ["20", "50", "100"],
}));

function percentOf(count: number) {
  if (!groupTotal.value) return "-";
  return `${((count / groupTotal.value) * 100).toFixed(1)}%`;
}

function buildDrillDown(record: any): LogDrillDownFilter {
  const time = props.filterState.toQueryParams();
  return {
    dimension: dimension.value,
    key: record.key,
    label: record.label,
    start: time.start,
    end: time.end,
  };
}

function buildStatsParams(extra?: Record<string, unknown>) {
  return props.filterState.buildSharedQueryParams({
    trend_granularity: trendGranularity.value,
    ...extra,
  });
}

function applyAutoGranularity() {
  const { start, end } = props.filterState.range.value;
  const rangeMinutes = end.diff(start, "minute", true);
  trendGranularity.value = resolveAutoTrendGranularity(props.filterState.preset.value, rangeMinutes);
}

async function fetchOverview() {
  const resp = await api.get("/api/v1/logs/stats", buildStatsParams());
  Object.assign(overview, {
    total: resp.data.total,
    blocked: resp.data.blocked,
    passed: resp.data.passed,
    trend: resp.data.trend || [],
    trend_modes: resp.data.trend_modes || [],
  });
}

function formatTrendLabel(value: string) {
  const formats: Record<TrendGranularity, string> = {
    "1m": "HH:mm",
    "5m": "HH:mm",
    "10m": "HH:mm",
    "30m": "HH:mm",
    "1h": "MM-DD HH:mm",
    "1d": "MM-DD",
    "1w": "MM-DD",
    "1mo": "YYYY-MM",
  };
  return formatDateTime(value, formats[trendGranularity.value]);
}

function onGranularitySelect({ key }: { key: string }) {
  const next = key as TrendGranularity;
  if (next === trendGranularity.value) return;
  trendGranularity.value = next;
  fetchOverviewOnly();
}

async function fetchOverviewOnly() {
  chartLoading.value = true;
  try {
    await fetchOverview();
  } finally {
    chartLoading.value = false;
    await renderCharts();
    setupChartObservers();
  }
}

function disposeChart(chart: ECharts | null) {
  chart?.dispose();
}

function renderTrendChart() {
  if (!trendChartEl.value || !overview.trend.length) {
    disposeChart(trendChart);
    trendChart = null;
    return;
  }
  disposeChart(trendChart);
  trendChart = echarts.init(trendChartEl.value, echartsThemeName(isDark.value));
  const times = overview.trend.map((item) => formatTrendLabel(item.time));
  const seriesDefs = buildTrendModeSeries(overview.trend, overview.trend_modes);
  const series = seriesDefs.map((s) => ({
    name: s.name,
    type: "line" as const,
    smooth: true,
    showSymbol: false,
    symbol: "none",
    itemStyle: { color: s.color },
    areaStyle: lineAreaGradient(s.color),
    data: overview.trend.map((item) => trendModeValue(item, s.key)),
  }));
  trendChart.setOption(prepareChartOption({
    color: seriesDefs.map((s) => s.color),
    tooltip: {
      trigger: "axis",
      formatter(params: unknown) {
        const items = Array.isArray(params) ? params : [params];
        const first = items[0] as { dataIndex?: number; marker?: string; seriesName?: string; value?: number };
        const idx = first?.dataIndex ?? 0;
        const timeLabel = formatDateTime(overview.trend[idx]?.time);
        const lines = items.map(
          (p) => `${(p as { marker?: string }).marker ?? ""}${(p as { seriesName?: string }).seriesName}: ${(p as { value?: number }).value ?? 0}`,
        );
        return `${timeLabel}<br/>${lines.join("<br/>")}`;
      },
    },
    legend: { data: series.map((item) => item.name), bottom: 0 },
    grid: { left: 8, right: 12, top: 16, bottom: 28, containLabel: true },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: times,
      show: false,
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      splitLine: { show: false },
    },
    series,
  }, isDark.value));
  trendChart.resize();
}

async function renderCharts() {
  await nextTick();
  renderTrendChart();
}

function setupChartObservers() {
  trendObserver?.disconnect();

  if (trendChartEl.value) {
    trendObserver = new ResizeObserver(() => trendChart?.resize());
    trendObserver.observe(trendChartEl.value);
  }
}

async function loadGroup() {
  const resp = await api.get("/api/v1/logs/stats/group", buildStatsParams({
    dimension: dimension.value,
    page: groupPage.value,
    page_size: groupPageSize.value,
  }));
  groupItems.value = localizeStatsItems(dimension.value, resp.data.items || [], {
    formatSiteId,
  });
  groupTotal.value = resp.data.total || 0;
  groupItemTotal.value = resp.data.group_total || 0;
  if (resp.data.page) groupPage.value = resp.data.page;
  if (resp.data.page_size) groupPageSize.value = resp.data.page_size;
}

let statsFetchSeq = 0;

async function fetchGroup() {
  const seq = ++statsFetchSeq;
  groupLoading.value = true;
  try {
    await loadGroup();
    if (seq !== statsFetchSeq) return;
  } finally {
    if (seq === statsFetchSeq) {
      groupLoading.value = false;
      await renderCharts();
      setupChartObservers();
    }
  }
}

async function fetchAll() {
  const seq = ++statsFetchSeq;
  groupPage.value = 1;
  chartLoading.value = true;
  groupLoading.value = true;
  try {
    await Promise.all([fetchOverview(), loadGroup()]);
    if (seq !== statsFetchSeq) return;
  } finally {
    if (seq === statsFetchSeq) {
      groupLoading.value = false;
      chartLoading.value = false;
      await renderCharts();
      setupChartObservers();
    }
  }
}

function selectDimension(key: StatsDimension) {
  if (dimension.value === key) return;
  dimension.value = key;
  groupPage.value = 1;
  fetchGroup();
}

function onTableChange(pagination: { current?: number; pageSize?: number }) {
  groupPage.value = pagination.current || 1;
  groupPageSize.value = pagination.pageSize || groupPageSize.value;
  fetchGroup();
}

function applyDimensionFromQuery(query: LocationQuery) {
  const next = resolveDimension(query);
  if (dimension.value === next) return false;
  dimension.value = next;
  groupPage.value = 1;
  return true;
}

function ensureLoaded() {
  if (initialized.value) return;
  initialized.value = true;
  applyAutoGranularity();
  fetchAll();
}

function applyFromQuery(query: LocationQuery) {
  applyDimensionFromQuery(query);
  initialized.value = true;
  applyAutoGranularity();
  fetchAll();
}

watch(
  () => props.active,
  (isActive) => {
    if (isActive) ensureLoaded();
  },
  { immediate: true },
);

watch(isDark, () => {
  if (!props.active || !initialized.value) return;
  void renderCharts();
});

watch(
  () => route.query.dimension,
  () => {
    if (!initialized.value) return;
    if (applyDimensionFromQuery(route.query)) {
      fetchGroup();
    }
  },
);

watch(
  () => [props.filterState.preset.value, props.filterState.customRange.value] as const,
  () => {
    if (!initialized.value) return;
    applyAutoGranularity();
  },
);

watch(
  () => props.filterState.refreshToken.value,
  () => {
    if (!initialized.value) return;
    fetchAll();
  },
);

defineExpose({ applyFromQuery, refresh: fetchAll });

onActivated(() => {
  trendChart?.resize();
});

onUnmounted(() => {
  trendObserver?.disconnect();
  disposeChart(trendChart);
});
</script>

<style scoped>
.log-stats-tab {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-row {
  margin: 0;
}

.result-panel {
  flex: 1;
  min-height: 0;
  height: auto;
}

.stats-body {
  display: grid;
  grid-template-columns: minmax(260px, 300px) 1fr;
  gap: 12px;
  align-items: stretch;
}

.dimension-panel {
  min-height: 0;
  height: 100%;
}

.result-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.dimension-panel :deep(.ant-card),
.result-panel :deep(.ant-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.dimension-panel :deep(.ant-card-body),
.result-panel :deep(.ant-card-body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.dimension-panel :deep(.ant-card-body) {
  padding: 10px 12px;
}

.dimension-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 2px;
}

.dimension-group + .dimension-group {
  margin-top: 12px;
}

.dimension-group-title {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 0.02em;
  margin-bottom: 6px;
}

.dimension-grid {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.dimension-btn {
  flex: 1 0 calc(30% - 6px);
  appearance: none;
  margin: 0;
  padding: 7px 6px;
  font-size: 12px;
  line-height: 1.35;
  border: 1px solid #6a6c6e30;
  border-radius: 6px;
  background: #c2c2c20d;
  color: var(--fs-text-secondary);
  cursor: pointer;
  text-align: center;
  transition:
    border-color 0.15s,
    background 0.15s,
    color 0.15s,
    box-shadow 0.15s;
}

.dimension-btn:hover {
  border-color: #40abde47;
  color: #0284c7;
}

.dimension-btn.active {
  border-color: #38bdf894;
  background: #29a9ff12;
  color: #048fdb;
  font-weight: 600;
}

.dimension-btn:focus-visible {
  outline: 2px solid #38bdf8;
  outline-offset: 1px;
}

.result-panel :deep(.ant-card-head-title) {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.panel-desc {
  font-size: 12px;
  font-weight: normal;
  color: #94a3b8;
}

.stats-chart {
  height: 220px;
}

.chart-content {
  min-height: 220px;
}

.chart-loading {
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-block + .chart-block {
  margin-top: 4px;
}

.chart-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.chart-block-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--fs-text-secondary);
  margin-bottom: 0;
}

.granularity-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin: 0;
  padding: 3px 6px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--fs-text-muted);
  background: var(--fs-bg);
  border: 1px solid var(--fs-border);
  border-radius: 6px;
  cursor: pointer;
  transition:
    border-color 0.15s,
    color 0.15s,
    background 0.15s;
}

.granularity-trigger:hover {
  color: var(--fs-color-primary);
  border-color: color-mix(in srgb, var(--fs-color-primary) 35%, var(--fs-border));
  background: color-mix(in srgb, var(--fs-color-primary) 8%, var(--fs-bg-muted));
}

.granularity-trigger:focus-visible {
  outline: 2px solid var(--fs-color-info);
  outline-offset: 1px;
}

.chart-empty {
  margin: 24px 0;
}

.stats-table {
  margin-top: 8px;
  font-size: 13px;
}

@media (max-width: 900px) {
  .stats-body {
    grid-template-columns: 1fr;
  }

  .summary-row :deep(.ant-col) {
    flex: 0 0 33.333333%;
    max-width: 33.333333%;
  }
}
</style>
