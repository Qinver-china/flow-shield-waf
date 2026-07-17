<template>
  <page-shell title="防护日志" description="多维统计分析与日志明细查询">
    <a-tabs v-model:active-key="activeTab" size="large" class="logs-tabs fs-tabs-animated">
      <a-tab-pane key="stats" tab="统计筛选" />
      <a-tab-pane key="detail" tab="日志明细" />
    </a-tabs>
    <fs-slide-transition :transition-key="activeTab">
      <log-stats-tab v-if="activeTab === 'stats'" ref="statsTabRef" @drill-down="onDrillDown" />
      <log-detail-tab
        v-else-if="activeTab === 'detail'"
        ref="detailTabRef"
        :drill-down="drillDown"
      />
    </fs-slide-transition>
  </page-shell>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api } from "@/api";
import PageShell from "@/components/PageShell.vue";
import FsSlideTransition from "@/components/FsSlideTransition.vue";
import LogDetailTab from "./logs/LogDetailTab.vue";
import LogStatsTab, { type LogDrillDownFilter } from "./logs/LogStatsTab.vue";

const route = useRoute();
const activeTab = ref("stats");
const drillDown = ref<LogDrillDownFilter | null>(null);
const detailTabRef = ref<InstanceType<typeof LogDetailTab> | null>(null);
const statsTabRef = ref<InstanceType<typeof LogStatsTab> | null>(null);

let heartbeatTimer: ReturnType<typeof setInterval> | null = null;

const detailQueryKeys = [
  "blocked",
  "mode",
  "source",
  "log_type",
  "client_ip",
  "rule_id",
  "geo_country",
  "method",
  "keyword",
];

function hasDetailFilters(query: Record<string, unknown>) {
  return detailQueryKeys.some((key) => query[key] !== undefined && query[key] !== "");
}

function applyRouteQuery() {
  const query = route.query;
  const tab = (query.tab as string) || (hasDetailFilters(query) ? "detail" : "stats");
  activeTab.value = tab;
  nextTick(() => {
    if (tab === "detail") {
      detailTabRef.value?.applyFromQuery(query);
    } else {
      statsTabRef.value?.applyFromQuery(query);
    }
  });
}

function sendHeartbeat(active: boolean) {
  api.post("/api/v1/logs/viewer-heartbeat", { active }).catch(() => {});
}

function onDrillDown(payload: LogDrillDownFilter) {
  drillDown.value = { ...payload };
  activeTab.value = "detail";
}

onMounted(() => {
  applyRouteQuery();
  sendHeartbeat(true);
  heartbeatTimer = setInterval(() => sendHeartbeat(true), 30000);
});

watch(
  () => route.query,
  () => applyRouteQuery(),
);

onUnmounted(() => {
  sendHeartbeat(false);
  if (heartbeatTimer) clearInterval(heartbeatTimer);
});
</script>

<style scoped>
.logs-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 12px;
}
</style>
