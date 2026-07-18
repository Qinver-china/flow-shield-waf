<template>
  <div class="log-detail-tab">
    <a-card size="small" title="筛选条件" class="filter-card">
      <a-form layout="vertical" class="filter-form">
        <div class="filter-quick-bar">
          <a-row :gutter="8" class="filter-quick-fields">
            <a-col :span="24" :xl="6">
              <a-form-item label="时间范围">
                <a-range-picker v-model:value="range" show-time style="width: 100%" />
              </a-form-item>
            </a-col>
            <a-col
              v-for="field in quickFilterFields"
              :key="field.key"
              v-bind="colSpanForField(field, true)"
            >
              <log-filter-field :field="field" :filters="filters" />
            </a-col>
          </a-row>

          <div class="filter-quick-actions">
            <a-button type="primary" @click="search">查询</a-button>
            <a-button @click="resetFilters">重置</a-button>
            <a-button class="filter-toggle" @click="toggleFiltersExpanded">
              {{ filtersExpanded ? "收起" : "展开" }}
              <up-outlined v-if="filtersExpanded" />
              <down-outlined v-else />
            </a-button>
          </div>
        </div>

        <template v-if="filtersExpanded">
          <section
            v-for="group in advancedFilterGroups"
            :key="group.label"
            class="filter-group"
          >
            <div class="filter-group-title">{{ group.label }}</div>
            <a-row :gutter="12">
              <a-col
                v-for="field in group.fields"
                :key="field.key"
                v-bind="colSpanForField(field)"
              >
                <log-filter-field :field="field" :filters="filters" />
              </a-col>
            </a-row>
          </section>
        </template>
      </a-form>
    </a-card>

    <a-card size="small" title="日志列表" class="list-card">
      <a-table
        :columns="columns"
        :data-source="rows"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        size="small"
        :scroll="{ x: 1100 }"
        @change="onTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'ts'">{{ formatTs(record.ts) }}</template>
          <template v-else-if="column.key === 'source'">
            <a-tag>{{ sourceLabel[record.source] || record.source || "-" }}</a-tag>
          </template>
          <template v-else-if="column.key === 'mode'">
            <a-tag :color="modeColor[record.mode] || 'default'">
              {{ modeLabel[record.mode] || record.mode || "-" }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'blocked'">
            <a-tag :color="record.blocked ? 'red' : 'green'">
              {{ record.blocked ? "拦截" : "放行" }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button type="link" size="small" @click="openDetail(record.id)">查看详情</a-button>
          </template>
        </template>
      </a-table>
    </a-card>

    <log-detail-drawer v-model:open="detailOpen" :log-id="detailId" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { useRoute, type LocationQuery } from "vue-router";
import type { Dayjs } from "dayjs";
import { DownOutlined, UpOutlined } from "@ant-design/icons-vue";
import { api } from "@/api";
import { nowInAppTz, toAppTz, toUtcIso } from "@/utils/datetime";
import LogDetailDrawer from "./LogDetailDrawer.vue";
import LogFilterField from "./LogFilterField.vue";
import {
  applyStatsDrillDownToFilters,
  buildAdvancedLogFilterGroups,
  buildLogQueryParams,
  createDefaultLogFilters,
  hydrateBotCategoryFilterOptions,
  logDetailFiltersUseAdvanced,
  logDetailQuickFilterFields,
  type StatsDimension,
} from "./constants";
import { formatTs } from "./useLogTimeRange";
import { colSpanForField } from "./useLogFilterField";
import type { LogDrillDownFilter } from "./LogStatsTab.vue";

const props = defineProps<{ drillDown?: LogDrillDownFilter | null }>();

const route = useRoute();

const quickFilterFields = logDetailQuickFilterFields;
const advancedFilterGroups = buildAdvancedLogFilterGroups();
const filtersExpanded = ref(false);

const columns = [
  { title: "时间", key: "ts", dataIndex: "ts", width: 168 },
  { title: "域名", dataIndex: "domain", width: 140, ellipsis: true },
  { title: "IP", dataIndex: "client_ip", width: 130 },
  { title: "方法", dataIndex: "method", width: 72 },
  { title: "URL", dataIndex: "uri", ellipsis: true },
  { title: "命中规则", dataIndex: "rule_name", width: 140, ellipsis: true },
  { title: "模式", key: "mode", dataIndex: "mode", width: 100 },
  { title: "来源", key: "source", dataIndex: "source", width: 110 },
  { title: "结果", key: "blocked", dataIndex: "blocked", width: 80 },
  { title: "操作", key: "action", width: 90, fixed: "right" as const },
];

const TEXT_FILTER_KEYS = [
  "rule_name",
  "action",
  "client_ip",
  "xff_first",
  "geo_region",
  "geo_city",
  "geo_isp",
  "geo_ip_type",
  "domain",
  "uri_path",
  "uri_ext",
  "referer_host",
  "keyword",
  "ua",
  "ua_family",
  "bot_name",
  "bot_category",
  "ua_os",
  "ua_browser",
  "tls_version",
] as const;

const SELECT_FILTER_KEYS = [
  "source",
  "mode",
  "log_type",
  "geo_country",
  "method",
  "scheme",
  "http_version",
  "bot_category",
] as const;

const rows = ref<any[]>([]);
const loading = ref(false);
const range = ref<[Dayjs, Dayjs]>([
  nowInAppTz().subtract(24, "hour"),
  nowInAppTz(),
]);
const filters = reactive<LogDetailFilters>(createDefaultLogFilters());
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

const detailOpen = ref(false);
const detailId = ref<string | null>(null);

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0,
  showTotal: (t: number) => `共 ${t} 条`,
  showSizeChanger: true,
});

function buildParams() {
  const params = buildLogQueryParams(
    filters,
    { page: page.value, page_size: pageSize.value },
    range.value?.length === 2
      ? { start: toUtcIso(range.value[0]), end: toUtcIso(range.value[1]) }
      : undefined,
  );
  return params;
}

let fetchSeq = 0;

async function fetchList() {
  const seq = ++fetchSeq;
  loading.value = true;
  try {
    const resp = await api.get("/api/v1/logs", buildParams());
    if (seq !== fetchSeq) return;
    rows.value = resp.data.items;
    total.value = resp.data.total;
    pagination.value = {
      ...pagination.value,
      current: page.value,
      pageSize: pageSize.value,
      total: total.value,
    };
  } finally {
    loading.value = false;
  }
}

function queryValue(query: LocationQuery, key: string) {
  const value = query[key];
  if (Array.isArray(value)) return value[0];
  return value;
}

function applyStringFilter(key: keyof LogDetailFilters, value: string | undefined) {
  if (!value) return;
  const current = filters[key];
  if (typeof current === "string") {
    filters[key] = value as never;
  }
}

function applyOptionalNumber(key: "rule_id" | "site_id" | "geo_asn", value: string | undefined) {
  if (!value) return;
  filters[key] = Number(value);
}

function syncExpandedFromFilters() {
  filtersExpanded.value = logDetailFiltersUseAdvanced(filters);
}

function toggleFiltersExpanded() {
  filtersExpanded.value = !filtersExpanded.value;
}

function applyFromQuery(query: LocationQuery) {
  Object.assign(filters, createDefaultLogFilters());
  const preset = queryValue(query, "preset");
  if (preset === "7d") {
    range.value = [nowInAppTz().subtract(7, "day"), nowInAppTz()];
  } else if (preset === "30d") {
    range.value = [nowInAppTz().subtract(30, "day"), nowInAppTz()];
  } else {
    range.value = [nowInAppTz().subtract(24, "hour"), nowInAppTz()];
  }

  const blocked = queryValue(query, "blocked");
  if (blocked === "true") filters.blocked = true;
  else if (blocked === "false") filters.blocked = false;

  const ipPrivate = queryValue(query, "ip_is_private");
  if (ipPrivate === "true") filters.ip_is_private = true;
  else if (ipPrivate === "false") filters.ip_is_private = false;

  for (const key of SELECT_FILTER_KEYS) {
    const value = queryValue(query, key);
    if (value) filters[key] = value;
  }

  for (const key of TEXT_FILTER_KEYS) {
    applyStringFilter(key, queryValue(query, key));
  }

  applyOptionalNumber("site_id", queryValue(query, "site_id"));
  applyOptionalNumber("rule_id", queryValue(query, "rule_id"));
  applyOptionalNumber("geo_asn", queryValue(query, "geo_asn"));

  syncExpandedFromFilters();
  page.value = 1;
  fetchList();
}

function applyDrillDown(payload: LogDrillDownFilter) {
  Object.assign(filters, createDefaultLogFilters());
  range.value = [toAppTz(payload.start), toAppTz(payload.end)];
  applyStatsDrillDownToFilters(payload.dimension as StatsDimension, payload.key, filters);
  syncExpandedFromFilters();
  page.value = 1;
  fetchList();
}

function search() {
  page.value = 1;
  fetchList();
}

function resetFilters() {
  Object.assign(filters, createDefaultLogFilters());
  range.value = [nowInAppTz().subtract(24, "hour"), nowInAppTz()];
  filtersExpanded.value = false;
  page.value = 1;
  fetchList();
}

function onTableChange(pg: any) {
  page.value = pg.current;
  pageSize.value = pg.pageSize;
  fetchList();
}

function openDetail(id: string) {
  detailId.value = id;
  detailOpen.value = true;
}

watch(
  () => props.drillDown,
  (value) => {
    if (value) applyDrillDown(value);
  },
  { immediate: true },
);

watch(
  () => route.query,
  (query) => {
    if (props.drillDown) return;
    applyFromQuery(query);
  },
);

onMounted(() => {
  void hydrateBotCategoryFilterOptions();
  if (!props.drillDown) applyFromQuery(route.query);
});

defineExpose({ applyDrillDown, applyFromQuery });
</script>

<style scoped>
.log-detail-tab {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-group + .filter-group {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #7777772e;
}

.filter-quick-bar {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.filter-quick-fields {
  flex: 1;
  min-width: 0;
}

.filter-quick-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 8px;
  padding-top: 30px;
}

.filter-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

@media (max-width: 1200px) {
  .filter-quick-bar {
    flex-direction: column;
  }

  .filter-quick-actions {
    width: 100%;
    padding-top: 0;
    justify-content: flex-end;
  }
}

.filter-group-title {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.filter-form :deep(.ant-form-item) {
  margin-bottom: 8px;
}

.filter-form :deep(.ant-form-item-label > label) {
  font-size: 13px;
}

.filter-form :deep(.ant-select) {
  width: 100%;
  min-width: 0;
}

.filter-form :deep(.ant-select-selection-item),
.filter-form :deep(.ant-select-selection-placeholder) {
  line-height: 30px;
}

.list-card :deep(.ant-card-body) {
  padding-top: 8px;
}
</style>
