<template>
  <page-shell title="防护日志" description="多维统计分析与日志明细查询">
    <log-filter-bar :filter-state="filterState" />

    <a-tabs v-model:active-key="activeTab" size="large" class="logs-tabs fs-tabs-animated">
      <a-tab-pane key="stats" tab="统计筛选" />
      <a-tab-pane key="detail" tab="日志明细" />
    </a-tabs>
    <fs-slide-transition :transition-key="activeTab">
      <log-stats-tab
        v-if="activeTab === 'stats'"
        ref="statsTabRef"
        :filter-state="filterState"
        @drill-down="onDrillDown"
      />
      <log-detail-tab
        v-else-if="activeTab === 'detail'"
        ref="detailTabRef"
        :filter-state="filterState"
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
import LogFilterBar from "./logs/LogFilterBar.vue";
import LogStatsTab, { type LogDrillDownFilter } from "./logs/LogStatsTab.vue";
import { useLogFilterState } from "./logs/useLogFilterState";

const route = useRoute();
const activeTab = ref("stats");
const filterState = useLogFilterState("6h");
const detailTabRef = ref<InstanceType<typeof LogDetailTab> | null>(null);
const statsTabRef = ref<InstanceType<typeof LogStatsTab> | null>(null);

let heartbeatTimer: ReturnType<typeof setInterval> | null = null;

function applyRouteQuery() {
  const query = route.query;
  const tab = (query.tab as string) || (hasDetailFilters(query) ? "detail" : "stats");
  activeTab.value = tab;
  filterState.applyFromRouteQuery(query);

  if (tab === "stats") {
    nextTick(() => {
      statsTabRef.value?.applyFromQuery(query);
    });
  }
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
];

function hasDetailFilters(query: Record<string, unknown>) {
  return detailQueryKeys.some((key) => query[key] !== undefined && query[key] !== "");
}

function onDrillDown(payload: LogDrillDownFilter) {
  filterState.applyDrillDown(payload);
  activeTab.value = "detail";
}

function sendHeartbeat(active: boolean) {
  api.post("/api/v1/logs/viewer-heartbeat", { active }).catch(() => {});
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
  margin-bottom: -4px;
}
</style>
