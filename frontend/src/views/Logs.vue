<template>
  <page-shell title="防护日志" description="多维统计分析与日志明细查询">
    <log-filter-bar :filter-state="filterState" />
     <a-tabs v-model:active-key="activeTab" size="large" class="logs-tabs fs-tabs-animated">
      <a-tab-pane key="stats" tab="统计筛选" />
      <a-tab-pane key="detail" tab="日志明细" />
    </a-tabs>
    <div class="logs-tab-panel">
      <transition name="logs-slide" @after-leave="onTabAfterLeave">
        <log-stats-tab
          v-show="visibleTab === 'stats'"
          ref="statsTabRef"
          :active="activeTab === 'stats'"
          :filter-state="filterState"
          @drill-down="onDrillDown"
        />
      </transition>
      <transition name="logs-slide" @after-leave="onTabAfterLeave">
        <log-detail-tab
          v-show="visibleTab === 'detail'"
          ref="detailTabRef"
          :active="activeTab === 'detail'"
          :filter-state="filterState"
        />
      </transition>
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

/** Currently shown pane (v-show). `null` = leave in progress (out-in). */
const visibleTab = ref<"stats" | "detail" | null>(activeTab.value);
let tabLeaveInFlight = false;
let pendingTab: "stats" | "detail" | null = null;

function onTabAfterLeave() {
  tabLeaveInFlight = false;
  const next = pendingTab ?? activeTab.value;
  pendingTab = null;
  visibleTab.value = next;
}

watch(activeTab, (next) => {
  if (next === visibleTab.value && !tabLeaveInFlight) return;
  pendingTab = next;
  if (tabLeaveInFlight) return;
  if (visibleTab.value == null) {
    visibleTab.value = next;
    pendingTab = null;
    return;
  }
  tabLeaveInFlight = true;
  // Hide current pane first; after-leave reveals pendingTab.
  visibleTab.value = null;
});

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
  // keep-alive 下 Logs 仍挂载；跳到 /rules?id=&drawer= 等外页时，
  // route.query 变化会误触发这里，把筛选/tab 清掉。只在日志页消费 query。
  if (route.path !== "/logs") return;

  const query = route.query as Record<string, unknown>;
  const key = routeQueryKey(query);
  if (key === lastRouteQueryKey) return;

  if (!hasLogNavQuery(query)) {
    // Empty query after a prior deep-link must clear sticky keep-alive filters.
    filterState.applyFromRouteQuery(route.query);
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
  api.post("/api/v1/logs/viewer-heartbeat", { active }).catch(() => { });
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
  position: relative;
  overflow: hidden;
  min-height: 0;
}

/* 对齐 fs-slide；由 visibleTab 串行切换实现 out-in，组件始终 v-show 不卸载 */
.logs-slide-enter-active,
.logs-slide-leave-active {
  transition:
    transform 220ms cubic-bezier(0.16, 1, 0.3, 1),
    opacity 220ms cubic-bezier(0.16, 1, 0.3, 1);
}

.logs-slide-enter-from,
.logs-slide-leave-to {
  transform: translateY(20px);
  opacity: 0;
}
</style>
