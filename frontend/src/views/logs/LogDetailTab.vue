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
          <template v-else-if="columnKey(column) === 'domain'">
            <log-dimension-action-cell
              v-if="record.domain"
              :label="record.domain"
              detail-field="domain"
              :detail-value="record.domain"
              :filter-state="filterState"
            />
            <span v-else>-</span>
          </template>
          <template v-else-if="columnKey(column) === 'client_ip'">
            <log-dimension-action-cell
              v-if="record.client_ip"
              :label="record.client_ip"
              detail-field="client_ip"
              :detail-value="record.client_ip"
              :filter-state="filterState"
            />
            <span v-else>-</span>
          </template>
          <template v-else-if="columnKey(column) === 'method'">
            <log-dimension-action-cell
              v-if="record.method"
              :label="record.method"
              detail-field="method"
              :detail-value="record.method"
              :filter-state="filterState"
            />
            <span v-else>-</span>
          </template>
          <template v-else-if="columnKey(column) === 'uri'">
            <log-dimension-action-cell
              v-if="record.uri"
              :label="record.uri"
              detail-field="uri"
              :detail-value="record.uri"
              :filter-state="filterState"
            />
            <span v-else>-</span>
          </template>
          <template v-else-if="columnKey(column) === 'source'">
            <log-dimension-action-cell
              v-if="record.source"
              :label="sourceLabel[record.source] || record.source"
              detail-field="source"
              :detail-value="record.source"
              :filter-state="filterState"
              variant="tag"
            />
            <span v-else>-</span>
          </template>
          <template v-else-if="columnKey(column) === 'mode'">
            <log-dimension-action-cell
              v-if="record.mode"
              :label="modeLabel[record.mode] || record.mode"
              detail-field="mode"
              :detail-value="record.mode"
              :filter-state="filterState"
              variant="tag"
              :tag-color="modeColor[record.mode] || 'default'"
            />
            <span v-else>-</span>
          </template>
          <template v-else-if="columnKey(column) === 'blocked'">
            <log-dimension-action-cell
              :label="record.blocked ? '拦截' : '放行'"
              detail-field="blocked"
              :detail-value="record.blocked ? 'true' : 'false'"
              :filter-state="filterState"
              variant="tag"
              :tag-color="record.blocked ? 'red' : 'green'"
            />
          </template>
          <template v-else-if="columnKey(column) === '__action'">
            <a-button type="link" size="small" @click="openDetail(record.id)">查看详情</a-button>
          </template>
          <template v-else-if="columnKey(column) === 'rule_name'">
            <log-dimension-action-cell
              v-if="record.rule_id"
              :label="record.rule_name || `规则 #${record.rule_id}`"
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
