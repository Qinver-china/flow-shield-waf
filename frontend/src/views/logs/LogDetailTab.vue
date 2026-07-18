<template>
  <div class="log-detail-tab">
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
        <template #bodyCell="{ column, record, text }">
          <template v-if="columnKey(column) === 'ts'">{{ formatTs(record.ts) }}</template>
          <template v-else-if="columnKey(column) === 'source'">
            <a-tag>{{ sourceLabel[record.source] || record.source || "-" }}</a-tag>
          </template>
          <template v-else-if="columnKey(column) === 'mode'">
            <a-tag :color="modeColor[record.mode] || 'default'">
              {{ modeLabel[record.mode] || record.mode || "-" }}
            </a-tag>
          </template>
          <template v-else-if="columnKey(column) === 'blocked'">
            <a-tag :color="record.blocked ? 'red' : 'green'">
              {{ record.blocked ? "拦截" : "放行" }}
            </a-tag>
          </template>
          <template v-else-if="columnKey(column) === '__action'">
            <a-button type="link" size="small" @click="openDetail(record.id)">查看详情</a-button>
          </template>
          <template v-else-if="columnKey(column) === 'rule_name'">
            <log-dimension-action-cell
              v-if="record.rule_id"
              :label="record.rule_name || `规则 #${record.rule_id}`"
              dimension="rule_id"
              :item-key="ruleItemKey(record)"
              :filter-state="filterState"
              :log-rule-record="record"
            />
            <span v-else>{{ record.rule_name || "-" }}</span>
          </template>
          <template v-else>{{ text }}</template>
        </template>
      </a-table>
    </a-card>

    <log-detail-drawer v-model:open="detailOpen" :log-id="detailId" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { api } from "@/api";
import LogDetailDrawer from "./LogDetailDrawer.vue";
import LogDimensionActionCell from "./LogDimensionActionCell.vue";
import { hydrateBotCategoryFilterOptions, modeColor, modeLabel, sourceLabel } from "./constants";
import { formatTs } from "./useLogTimeRange";
import type { LogFilterState } from "./useLogFilterState";

const props = defineProps<{
  filterState: LogFilterState;
}>();

const columns = [
  { title: "时间", key: "ts", dataIndex: "ts", width: 168 },
  { title: "域名", key: "domain", dataIndex: "domain", width: 140, ellipsis: true },
  { title: "IP", key: "client_ip", dataIndex: "client_ip", width: 130 },
  { title: "方法", key: "method", dataIndex: "method", width: 72 },
  { title: "URL", key: "uri", dataIndex: "uri", ellipsis: true },
  { title: "命中规则", key: "rule_name", dataIndex: "rule_name", width: 140, ellipsis: true },
  { title: "防护方式", key: "mode", dataIndex: "mode", width: 100 },
  { title: "来源", key: "source", dataIndex: "source", width: 110 },
  { title: "结果", key: "blocked", dataIndex: "blocked", width: 80 },
  { title: "操作", key: "__action", width: 90, fixed: "right" as const },
];

function columnKey(column: { key?: string; dataIndex?: string | string[] }) {
  if (column.key) return column.key;
  if (Array.isArray(column.dataIndex)) return column.dataIndex.join(".");
  return column.dataIndex;
}

const rows = ref<any[]>([]);
const loading = ref(false);
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

let fetchSeq = 0;

async function fetchList() {
  const seq = ++fetchSeq;
  loading.value = true;
  try {
    const resp = await api.get(
      "/api/v1/logs",
      props.filterState.buildDetailQueryParams({
        page: page.value,
        page_size: pageSize.value,
      }),
    );
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

function refresh() {
  page.value = 1;
  fetchList();
}

function onTableChange(pg: any) {
  page.value = pg.current;
  pageSize.value = pg.pageSize;
  fetchList();
}

function ruleItemKey(record: { source?: string | null; rule_id?: number | null }) {
  if (!record.rule_id) return "";
  return record.source ? `${record.source}:${record.rule_id}` : String(record.rule_id);
}

function openDetail(id: string) {
  detailId.value = id;
  detailOpen.value = true;
}

watch(
  () => props.filterState.refreshToken.value,
  () => {
    page.value = 1;
    fetchList();
  },
);

onMounted(() => {
  void hydrateBotCategoryFilterOptions();
  fetchList();
});

defineExpose({ refresh });
</script>

<style scoped>
.log-detail-tab {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.list-card :deep(.ant-card-body) {
  padding-top: 8px;
}
</style>
