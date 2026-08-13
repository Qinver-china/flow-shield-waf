<template>
  <page-shell title="证书管理" description="导入与管理 SSL/TLS 证书，供站点 HTTPS 使用">
    <template #actions>
      <a-button type="primary" @click="openCreate">导入证书</a-button>
      <a-button @click="panelImportOpen = true">从其他面板导入</a-button>
    </template>

    <list-filter-bar
      :fields="listFilters"
      :model="filterValues"
      @change="onFilterChange"
      @reset="resetFilters"
    />

    <fs-data-table
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="pagination"
      api-base="/api/v1/certificates"
      :batch="{ allowDelete: true, enableToggle: false }"
      :scroll="{ x: 1100 }"
      @change="onTableChange"
      @refresh="fetchList"
    >
      <template #bodyCell="{ column, record, text }">
        <template v-if="column.key === 'not_after'">
          <a-tooltip v-if="record.not_after" :title="formatTime(record.not_after)">
            <span :class="expiryClass(record.not_after)">{{ formatRemainingDays(record.not_after) }}</span>
          </a-tooltip>
          <span v-else>-</span>
        </template>
        <template v-else-if="column.key === 'bound_sites'">
          {{ formatBoundSites(record.bound_sites) }}
        </template>
        <template v-else-if="column.key === 'expiry_notify'">
          <template v-if="!record.expiry_notify_enabled">关闭</template>
          <template v-else>
            <div>已开启</div>
            <div class="notify-channel">{{ formatNotifyChannels(record.expiry_notify_channel_ids) }}</div>
          </template>
        </template>
        <template v-else-if="column.key === '__actions'">
          <a @click="openUpdate(record)">更新证书</a>
          <a-divider type="vertical" />
          <a-popconfirm title="确认删除该证书?" @confirm="remove(record.id)">
            <a class="danger">删除</a>
          </a-popconfirm>
        </template>
        <template v-else>
          {{ text ?? "-" }}
        </template>
      </template>
    </fs-data-table>

    <certificate-form-drawer
      v-model:open="modalOpen"
      :certificate-id="editingId"
      @saved="fetchList"
    />
    <panel-import-drawer
      v-model:open="panelImportOpen"
      kind="certificates"
      @imported="fetchList"
    />
  </page-shell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { message } from "ant-design-vue";
import { api } from "@/api";
import CertificateFormDrawer from "@/components/CertificateFormDrawer.vue";
import PanelImportDrawer from "@/components/PanelImportDrawer.vue";
import FsDataTable from "@/components/FsDataTable.vue";
import ListFilterBar from "@/components/ListFilterBar.vue";
import PageShell from "@/components/PageShell.vue";
import { certificateExpiryFilterOptions } from "@/constants/resourceList";
import { formatDateTime, parseUtc } from "@/utils/datetime";
import type { ResourceFilterField } from "@/types/resourceList";

interface CertificateBoundSite {
  id: number;
  name: string;
}

interface CertificateRow {
  id: number;
  name: string;
  domains: string | null;
  not_before: string | null;
  not_after: string | null;
  remark: string | null;
  expiry_notify_enabled?: boolean;
  expiry_notify_channel_ids?: number[];
  bound_sites?: CertificateBoundSite[];
}

interface NotificationChannelItem {
  id: number;
  name: string;
  channel_type: string;
  enabled: boolean;
}

const panelImportOpen = ref(false);

const listFilters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "名称 / 域名 / 备注" },
  {
    key: "expiry",
    label: "到期状态",
    type: "select",
    width: "180px",
    options: certificateExpiryFilterOptions,
  },
];

const columns = computed(() => [
  {
    title: "名称",
    dataIndex: "name",
    sorter: true,
    sortOrder: sortField.value === "name" ? (sortOrder.value === "asc" ? "ascend" : "descend") : undefined,
  },
  { title: "域名", dataIndex: "domains", ellipsis: true },
  {
    title: "已绑定站点",
    key: "bound_sites",
    ellipsis: true,
    width: 180,
  },
  {
    title: "到期时间",
    key: "not_after",
    dataIndex: "not_after",
    width: 120,
    sorter: true,
    sortOrder:
      sortField.value === "not_after" ? (sortOrder.value === "asc" ? "ascend" : "descend") : undefined,
  },
  {
    title: "到期前通知",
    key: "expiry_notify",
    width: 200,
  },
  { title: "备注", dataIndex: "remark", ellipsis: true },
  { title: "操作", key: "__actions", width: 180 },
]);

const rows = ref<CertificateRow[]>([]);
const channels = ref<NotificationChannelItem[]>([]);
const loading = ref(false);
const modalOpen = ref(false);
const editingId = ref<number | null>(null);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const filterValues = reactive<Record<string, unknown>>({});
const sortField = ref<string | undefined>();
const sortOrder = ref<"asc" | "desc" | undefined>("desc");

const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showTotal: (t: number) => `共 ${t} 条`,
}));

function formatTime(value: string | null) {
  return formatDateTime(value);
}

function formatRemainingDays(notAfter: string | null) {
  if (!notAfter) return "-";
  const ms = parseUtc(notAfter).valueOf() - Date.now();
  const dayMs = 24 * 3600 * 1000;
  if (ms < 0) {
    const overdue = Math.max(1, Math.ceil(-ms / dayMs));
    return `已过期 ${overdue} 天`;
  }
  const remaining = Math.max(0, Math.ceil(ms / dayMs));
  return `剩余 ${remaining} 天`;
}

function formatNotifyChannels(channelIds: number[] | null | undefined) {
  if (!channelIds?.length) return "未选择通道";
  return channelIds
    .map((id) => channels.value.find((item) => item.id === id)?.name || `#${id}`)
    .join("、");
}

function formatBoundSites(sites: CertificateBoundSite[] | null | undefined) {
  if (!sites?.length) return "-";
  return sites.map((site) => site.name).join("、");
}

function expiryClass(notAfter: string | null) {
  if (!notAfter) return "";
  const diff = parseUtc(notAfter).valueOf() - Date.now();
  if (diff < 0) return "expired";
  if (diff < 30 * 24 * 3600 * 1000) return "soon";
  return "";
}

async function loadChannels() {
  try {
    const resp = await api.get<NotificationChannelItem[]>("/api/v1/notification-channels");
    channels.value = resp.data || [];
  } catch {
    channels.value = [];
  }
}

async function fetchList() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize.value,
    };
    if (sortField.value && sortOrder.value) {
      params.sort_by = sortField.value;
      params.sort_order = sortOrder.value;
    }
    for (const field of listFilters) {
      const value = filterValues[field.key];
      if (value !== undefined && value !== null && value !== "") {
        params[field.key] = value;
      }
    }
    const resp = await api.get("/api/v1/certificates", params);
    rows.value = resp.data.items;
    total.value = resp.data.total;
  } finally {
    loading.value = false;
  }
}

function onTableChange(pg: any, _filters: any, sorter: any) {
  page.value = pg.current;
  pageSize.value = pg.pageSize;
  const active = Array.isArray(sorter) ? sorter.find((item) => item.order) : sorter;
  if (active?.order) {
    sortField.value = active.field || active.columnKey;
    sortOrder.value = active.order === "ascend" ? "asc" : "desc";
  } else {
    sortField.value = undefined;
    sortOrder.value = "desc";
  }
  fetchList();
}

function onFilterChange() {
  page.value = 1;
  fetchList();
}

function resetFilters() {
  for (const field of listFilters) {
    filterValues[field.key] = undefined;
  }
  page.value = 1;
  fetchList();
}

function openCreate() {
  editingId.value = null;
  modalOpen.value = true;
}

function openUpdate(row: CertificateRow) {
  editingId.value = row.id;
  modalOpen.value = true;
}

async function remove(id: number) {
  await api.del(`/api/v1/certificates/${id}`);
  message.success("已删除");
  fetchList();
}

onMounted(async () => {
  await loadChannels();
  await fetchList();
});
</script>

<style scoped>
.danger {
  color: #ef4444;
}
.expired {
  color: #ef4444;
}
.soon {
  color: #f59e0b;
}
.notify-channel {
  margin-top: 2px;
  font-size: 12px;
  color: var(--fs-text-muted, #64748b);
}
</style>
