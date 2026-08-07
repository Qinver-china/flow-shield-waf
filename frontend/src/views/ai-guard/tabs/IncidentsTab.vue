<template>
  <div>
    <a-table
      v-if="!isMobile"
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="resolvedPagination"
      row-key="id"
      bordered
      class="incidents-table"
      :scroll="{ x: 960 }"
      :show-sorter-tooltip="false"
      @change="onTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-else-if="column.dataIndex === 'created_at'">
          {{ formatDateTime(record.created_at) }}
        </template>
        <template v-else-if="column.key === 'summary'">
          <a-typography-text
            class="incident-summary"
            :ellipsis="{ tooltip: true }"
            :content="record.analysis_report?.summary || '—'"
          />
        </template>
        <template v-else-if="column.key === 'actions'">
          <a v-if="record.status === 'suggested'" @click="apply(record.id)">应用规则</a>
          <a-divider v-if="record.status === 'suggested'" type="vertical" />
          <a v-if="record.applied_rule_id" @click="rollback(record.id)">回滚</a>
          <a-divider v-if="record.applied_rule_id" type="vertical" />
          <a @click="showDetail(record)">详情</a>
          <a-divider type="vertical" />
          <a-popconfirm
            v-if="record.status !== 'dismissed'"
            title="确认忽略？"
            @confirm="dismiss(record.id)"
          >
            <a>忽略</a>
          </a-popconfirm>
        </template>
      </template>
    </a-table>

    <fs-mobile-table-cards
      v-else
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="resolvedPagination"
      row-key="id"
      :exclude-keys="['actions', 'status', 'created_at']"
      @change="onTableChange"
    >
      <template #head="{ record }">
        <div class="incident-head">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
          <span class="incident-time">{{ formatDateTime(record.created_at) }}</span>
        </div>
      </template>
      <template #cell="{ column, record }">
        <template v-if="column.key === 'summary'">
          {{ record.analysis_report?.summary || "—" }}
        </template>
        <template v-else-if="column.dataIndex === 'applied_rule_id'">
          {{ record.applied_rule_id || "—" }}
        </template>
        <template v-else-if="column.key === 'actions'">
          <a v-if="record.status === 'suggested'" @click="apply(record.id)">应用规则</a>
          <a-divider v-if="record.status === 'suggested'" type="vertical" />
          <a v-if="record.applied_rule_id" @click="rollback(record.id)">回滚</a>
          <a-divider v-if="record.applied_rule_id" type="vertical" />
          <a @click="showDetail(record)">详情</a>
          <a-divider v-if="record.status !== 'dismissed'" type="vertical" />
          <a-popconfirm
            v-if="record.status !== 'dismissed'"
            title="确认忽略？"
            @confirm="dismiss(record.id)"
          >
            <a>忽略</a>
          </a-popconfirm>
        </template>
      </template>
    </fs-mobile-table-cards>

    <fs-detail-drawer
      v-model:open="drawerOpen"
      title="分析详情"
      :subtitle="detail?.id ? `事件 #${detail.id}` : undefined"
      :width="720"
      :json-content="detail?.log_sample_meta ? JSON.stringify(detail.log_sample_meta, null, 2) : undefined"
      json-title="日志样本元数据"
    >
      <template v-if="detail">
        <fs-detail-section title="分析结果">
          <fs-detail-kv :items="summaryItems" />
        </fs-detail-section>

        <fs-detail-section v-if="detail.analysis_report?.attack_indicators?.length" title="攻击共性">
          <ul class="indicator-list">
            <li v-for="(item, i) in detail.analysis_report.attack_indicators" :key="i">{{ item }}</li>
          </ul>
        </fs-detail-section>

        <fs-detail-section v-if="detail.suggested_rule?.conditions" title="建议规则">
          <rule-draft-preview :conditions="detail.suggested_rule.conditions" />
        </fs-detail-section>
      </template>
    </fs-detail-drawer>
  </div>
</template>

<script setup lang="ts">
import { message, Modal } from "ant-design-vue";
import { computed, onMounted, reactive, ref } from "vue";
import { api } from "@/api";
import FsDetailDrawer from "@/components/FsDetailDrawer.vue";
import FsDetailKv from "@/components/FsDetailKv.vue";
import FsDetailSection from "@/components/FsDetailSection.vue";
import FsMobileTableCards from "@/components/FsMobileTableCards.vue";
import { useResponsivePagination } from "@/composables/useResponsivePagination";
import { formatDateTime } from "@/utils/datetime";
import RuleDraftPreview from "../components/RuleDraftPreview.vue";

const loading = ref(false);
const rows = ref<any[]>([]);
const page = ref(1);
const pageSize = ref(20);
const drawerOpen = ref(false);
const detail = ref<any>(null);

const { isMobile, withPaginationSize } = useResponsivePagination();

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
});

const resolvedPagination = computed(() => withPaginationSize(pagination));

const columns = [
  { title: "状态", key: "status", width: 100 },
  { title: "分析摘要", key: "summary", width: 460, ellipsis: true },
  { title: "应用规则", dataIndex: "applied_rule_id", width: 100 },
  { title: "时间", dataIndex: "created_at", width: 180 },
  { title: "操作", key: "actions", width: 100, fixed: "right" as const },
];

const summaryItems = computed(() => {
  const d = detail.value;
  if (!d) return [];
  const items = [
    { label: "状态", value: statusLabel(d.status), tag: true, tagColor: statusColor(d.status) },
  ];
  if (d.analysis_report?.summary) {
    items.push({ label: "摘要", value: d.analysis_report.summary });
  }
  if (d.analysis_report?.confidence != null) {
    items.push({
      label: "置信度",
      value: `${(d.analysis_report.confidence * 100).toFixed(0)}%`,
    });
  }
  return items;
});

const INCIDENT_STATUS_LABELS: Record<string, string> = {
  pending: "待处理",
  analyzing: "分析中",
  suggested: "待应用",
  analyzed: "仅分析",
  applied: "已应用",
  failed: "失败",
  dismissed: "已忽略",
};

function statusLabel(s: string) {
  return INCIDENT_STATUS_LABELS[s] || s;
}

function statusColor(s: string) {
  const map: Record<string, string> = {
    pending: "default",
    suggested: "orange",
    analyzed: "cyan",
    applied: "green",
    failed: "red",
    analyzing: "blue",
    dismissed: "default",
  };
  return map[s] || "default";
}

async function load() {
  loading.value = true;
  try {
    const res = await api.get("/api/v1/ai-guard/incidents", {
      page: page.value,
      page_size: pageSize.value,
    });
    rows.value = res.data.items;
    pagination.total = res.data.total;
    pagination.current = res.data.page;
  } finally {
    loading.value = false;
  }
}

function onTableChange(pag: { current?: number; pageSize?: number }) {
  page.value = pag.current || 1;
  pageSize.value = pag.pageSize || 20;
  load();
}

function showDetail(record: any) {
  detail.value = record;
  drawerOpen.value = true;
}

async function apply(id: number) {
  Modal.confirm({
    title: "应用 AI 建议的规则？",
    onOk: async () => {
      await api.post(`/api/v1/ai-guard/incidents/${id}/apply`, {});
      message.success("规则已应用");
      await load();
    },
  });
}

async function rollback(id: number) {
  Modal.confirm({
    title: "回滚将删除 AI 创建的规则，确认？",
    onOk: async () => {
      await api.post(`/api/v1/ai-guard/incidents/${id}/rollback`);
      message.success("已回滚");
      await load();
    },
  });
}

async function dismiss(id: number) {
  await api.post(`/api/v1/ai-guard/incidents/${id}/dismiss`);
  message.success("已忽略");
  await load();
}

onMounted(load);
</script>

<style scoped>
.incidents-table :deep(.ant-table) {
  table-layout: fixed;
}

.incident-summary {
  display: block;
  max-width: 100%;
  color: inherit;
}

.incident-head {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: space-between;
}

.incident-time {
  font-size: 12px;
  color: var(--fs-text-muted);
}

.indicator-list {
  margin: 0;
  padding-left: 20px;
  color: var(--fs-text-primary);
  font-size: 13px;
  line-height: 1.7;
}
</style>
