<template>
  <page-shell title="防护日志" description="多维统计分析与日志明细查询">
    <log-filter-bar :filter-state="filterState" />

    <a-tabs v-model:active-key="activeTab" size="large" class="logs-tabs fs-tabs-animated">
      <a-tab-pane key="stats" tab="统计筛选" />
      <a-tab-pane key="detail" tab="日志明细" />
    </a-tabs>
    <div class="logs-tab-panel">
      <log-stats-tab
        v-show="activeTab === 'stats'"
        ref="statsTabRef"
        :active="activeTab === 'stats'"
        :filter-state="filterState"
        @drill-down="onDrillDown"
      />
      <log-detail-tab
        v-show="activeTab === 'detail'"
        ref="detailTabRef"
        :active="activeTab === 'detail'"
        :filter-state="filterState"
      />
    </div>
  </page-shell>
</template>

<script setup lang="ts">
import { nextTick, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api } from "@/api";
import PageShell from "@/components/PageShell.vue";
import LogDetailTab from "./logs/LogDetailTab.vue";
import LogFilterBar from "./logs/LogFilterBar.vue";
import LogStatsTab, { type LogDrillDownFilter } from "./logs/LogStatsTab.vue";
import { logsPageActiveTab } from "./logs/logsPageSession";
import { useLogFilterState } from "./logs/useLogFilterState";

defineOptions({ name: "Logs" });

const route = useRoute();
const activeTab = logsPageActiveTab;
const filterState = useLogFilterState("6h");
const detailTabRef = ref<InstanceType<typeof LogDetailTab> | null>(null);
const statsTabRef = ref<InstanceType<typeof LogStatsTab> | null>(null);

let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let lastRouteQueryKey = "";

function routeQueryKey(query: Record<string, unknown>) {
  return JSON.stringify(query);
}

function hasLogNavQuery(query: Record<string, unknown>) {
  return Object.keys(query).some((key) => {
    const value = query[key];
    return value !== undefined && value !== null && value !== "";
  });
}

const detailQueryKeys = [
  "blocked",
  "mode",
  "source",
  "log_type",
  "client_ip",
  "rule_id",
  "site_id",
  "bot_name",
  "bot_category",
  "geo_country",
  "method",
  "keyword",
  "tab",
  "preset",
  "dimension",
  "start",
  "end",
];

function hasDetailFilters(query: Record<string, unknown>) {
  return detailQueryKeys.some((key) => query[key] !== undefined && query[key] !== "");
}

function applyRouteQuery() {
  const query = route.query as Record<string, unknown>;
  const key = routeQueryKey(query);
  if (key === lastRouteQueryKey) return;

  if (!hasLogNavQuery(query)) {
    lastRouteQueryKey = key;
    return;
  }

  const tab = (query.tab as string) || (hasDetailFilters(query) ? "detail" : "stats");
  activeTab.value = tab === "detail" ? "detail" : "stats";
  filterState.applyFromRouteQuery(route.query);

  if (activeTab.value === "stats") {
    nextTick(() => {
      statsTabRef.value?.applyFromQuery(route.query);
    });
  }

  lastRouteQueryKey = key;
}

function onDrillDown(payload: LogDrillDownFilter) {
  filterState.applyDrillDown(payload);
  activeTab.value = "detail";
}

function sendHeartbeat(active: boolean) {
  api.post("/api/v1/logs/viewer-heartbeat", { active }).catch(() => {});
}

function startHeartbeat() {
  sendHeartbeat(true);
  if (!heartbeatTimer) {
    heartbeatTimer = setInterval(() => sendHeartbeat(true), 30000);
  }
}

function stopHeartbeat() {
  sendHeartbeat(false);
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

onMounted(() => {
  applyRouteQuery();
  startHeartbeat();
});

onActivated(() => {
  startHeartbeat();
});

onDeactivated(() => {
  stopHeartbeat();
});

watch(
  () => route.query,
  () => applyRouteQuery(),
);

onUnmounted(() => {
  stopHeartbeat();
});
</script>

<style scoped>
.logs-tabs :deep(.ant-tabs-nav) {
  margin-bottom: -4px;
}

.logs-tab-panel {
  min-height: 0;
}
</style>
