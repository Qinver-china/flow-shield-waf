<template>
  <div>
    <a-alert
      type="info"
      show-icon
      style="margin-bottom: 16px"
      message="当流量或拦截率达到阈值时，AI 将自动分析近期日志并生成防护规则。可配置仅建议、自动观察或自动拦截。"
    />

    <fs-data-table
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="pagination"
      api-base="/api/v1/ai-guard/policies"
      :batch="batchConfig"
      has-enabled-column
      @change="onTableChange"
      @refresh="load"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'trigger'">
          <div>{{ triggerLabel(record.trigger_type) }}</div>
          <div class="sub">{{ formatTriggerParams(record) }}</div>
        </template>
        <template v-else-if="column.key === 'apply_mode'">
          {{ applyModeLabel(record.apply_mode) }}
        </template>
        <template v-else-if="column.key === 'enabled'">
          <a-switch :checked="record.enabled" @change="(v: boolean) => toggle(record, v)" />
        </template>
        <template v-else-if="column.key === 'actions'">
          <a @click="openEdit(record)">编辑</a>
          <a-divider type="vertical" />
          <a-popconfirm title="确认删除？" @confirm="remove(record.id)">
            <a class="danger">删除</a>
          </a-popconfirm>
        </template>
      </template>
    </fs-data-table>

    <fs-form-drawer
      v-model:open="modalOpen"
      title="防护策略"
      :subtitle="form.id ? `#${form.id}` : undefined"
      :mode="form.id ? 'edit' : 'create'"
      :width="720"
      :confirm-loading="saving"
      @ok="save"
    >
      <defense-policy-form v-model="form" :triggers="triggers" :channels="channels" />
    </fs-form-drawer>
  </div>
</template>

<script setup lang="ts">
import { message } from "ant-design-vue";
import { onMounted, reactive, ref } from "vue";
import { api } from "@/api";
import FsDataTable from "@/components/FsDataTable.vue";
import FsFormDrawer from "@/components/FsFormDrawer.vue";
import DefensePolicyForm from "../components/DefensePolicyForm.vue";
import { applyModeOptions, commonBatchEditFields } from "@/constants/batch";
import { trafficWindowLabels } from "@/views/logs/constants";
import type { BatchConfig } from "@/types/batch";

const loading = ref(false);
const saving = ref(false);
const modalOpen = ref(false);
const rows = ref<any[]>([]);
const triggers = ref<any[]>([]);
const channels = ref<any[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
});

const columns = [
  { title: "名称", dataIndex: "name", key: "name" },
  { title: "触发条件", key: "trigger" },
  { title: "应用模式", key: "apply_mode", width: 140 },
  { title: "启用", key: "enabled", width: 80 },
  { title: "操作", key: "actions", width: 120 },
];

const batchConfig: BatchConfig = {
  modeOptions: applyModeOptions,
  modeField: "apply_mode",
  editFields: [commonBatchEditFields.enabled],
};

const defaultForm = () => ({
  id: null as number | null,
  name: "",
  enabled: true,
  trigger_type: "traffic.qps_gt",
  trigger_params: { window_sec: 60, qps: 100 },
  apply_mode: "suggest_only",
  notify_on: ["trigger", "result"],
  channel_ids: [] as number[],
  cooldown_sec: 300,
  remark: "",
});

const form = ref(defaultForm());

function triggerLabel(t: string) {
  return triggers.value.find((x) => x.type === t)?.label || t;
}

function formatTriggerParams(record: any) {
  const meta = triggers.value.find((t) => t.type === record.trigger_type);
  const params = record.trigger_params || {};
  if (!meta?.params?.length) return "—";

  const parts: string[] = [];
  for (const p of meta.params) {
    const value = params[p.key];
    if (value == null || value === "") continue;

    let display = String(value);
    if (p.key === "window_sec") {
      display = trafficWindowLabels[Number(value)] || `${value} 秒`;
    } else if (p.key === "window_min") {
      display = `${value} 分钟`;
    } else if (p.key === "percent") {
      display = `${value}%`;
    } else if (p.key === "site_id") {
      display = `站点 #${value}`;
    }

    parts.push(`${p.label || p.key} ${display}`);
  }
  return parts.join(" · ") || "—";
}

function applyModeLabel(m: string) {
  const map: Record<string, string> = {
    suggest_only: "仅建议",
    auto_observe: "自动观察",
    auto_block: "自动拦截",
  };
  return map[m] || m;
}

async function load() {
  loading.value = true;
  try {
    const res = await api.get("/api/v1/ai-guard/policies", {
      page: page.value,
      page_size: pageSize.value,
    });
    rows.value = res.data.items;
    total.value = res.data.total;
    pagination.total = res.data.total;
    pagination.current = res.data.page;
  } finally {
    loading.value = false;
  }
}

async function loadMeta() {
  const [tRes, cRes] = await Promise.all([
    api.get("/api/v1/ai-guard/policies/meta/triggers"),
    api.get("/api/v1/notification-channels"),
  ]);
  triggers.value = tRes.data.triggers || [];
  channels.value = cRes.data || [];
}

function onTableChange(pag: { current?: number; pageSize?: number }) {
  page.value = pag.current || 1;
  pageSize.value = pag.pageSize || 20;
  load();
}

function openCreate() {
  form.value = defaultForm();
  modalOpen.value = true;
}

function openEdit(record: any) {
  form.value = { ...record, trigger_params: { ...record.trigger_params } };
  modalOpen.value = true;
}

async function save() {
  saving.value = true;
  try {
    const payload = { ...form.value };
    delete payload.id;
    if (form.value.id) {
      await api.put(`/api/v1/ai-guard/policies/${form.value.id}`, payload);
    } else {
      await api.post("/api/v1/ai-guard/policies", payload);
    }
    message.success("已保存");
    modalOpen.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}

async function remove(id: number) {
  await api.del(`/api/v1/ai-guard/policies/${id}`);
  message.success("已删除");
  await load();
}

async function toggle(record: any, enabled: boolean) {
  const prev = record.enabled;
  record.enabled = enabled;
  try {
    await api.put(`/api/v1/ai-guard/policies/${record.id}`, { enabled });
  } catch {
    record.enabled = prev;
  }
}

onMounted(async () => {
  await loadMeta();
  await load();
});

defineExpose({ openCreate });
</script>

<style scoped>
.sub {
  font-size: 12px;
  color: #888;
}
.danger {
  color: #ff4d4f;
}
</style>
