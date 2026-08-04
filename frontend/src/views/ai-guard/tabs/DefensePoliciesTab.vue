<template>
  <div>
    <a-alert
      type="info"
      show-icon
      style="margin-bottom: 16px"
      message="当流量或拦截率达到阈值时，AI 将自动分析近期日志和请求数据并生成防护规则。"
    />

    <fs-data-table
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="pagination"
      api-base="/api/v1/ai-guard/policies"
      :batch="batchConfig"
      has-enabled-column
      mobile-title-key="name"
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
      <defense-policy-form
        v-model="form"
        :triggers="triggers"
        :channels="channels"
        :traffic-windows="trafficWindows"
        :block-windows="blockWindows"
        :system-windows="systemWindows"
      />
    </fs-form-drawer>
  </div>
</template>

<script setup lang="ts">
import { message } from "ant-design-vue";
import { onMounted, reactive, ref } from "vue";
import { api } from "@/api";
import FsDataTable from "@/components/FsDataTable.vue";
import FsFormDrawer from "@/components/FsFormDrawer.vue";
import { useSiteOptions } from "@/composables/useSiteOptions";
import DefensePolicyForm from "../components/DefensePolicyForm.vue";
import { applyModeOptions, commonBatchEditFields } from "@/constants/batch";
import type { BatchConfig } from "@/types/batch";

const { formatSiteId } = useSiteOptions();

const loading = ref(false);
const saving = ref(false);
const modalOpen = ref(false);
const rows = ref<any[]>([]);
const triggers = ref<any[]>([]);
const channels = ref<any[]>([]);
const trafficWindows = ref([
  { value: 10, label: "10 秒" },
  { value: 30, label: "30 秒" },
  { value: 60, label: "1 分钟" },
  { value: 300, label: "5 分钟" },
  { value: 1800, label: "30 分钟" },
  { value: 3600, label: "60 分钟" },
]);
const blockWindows = ref([
  { value: 5, label: "5 分钟" },
  { value: 15, label: "15 分钟" },
  { value: 30, label: "30 分钟" },
  { value: 60, label: "60 分钟" },
]);
const systemWindows = ref([
  { value: 60, label: "1 分钟" },
  { value: 300, label: "5 分钟" },
  { value: 1800, label: "30 分钟" },
]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
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

/** Default trigger params aligned with alert policy defaults. */
function defaultParamsFor(type: string): Record<string, unknown> {
  if (type === "traffic.burst_logging") return {};
  if (type.startsWith("traffic.baseline")) return { window_sec: 300, percent: 50 };
  if (type.startsWith("traffic.abs")) return { window_sec: 300, threshold: 1000 };
  if (type.startsWith("traffic.qps")) return { window_sec: 60, threshold: 100 };
  if (type === "security.block_count") return { window_min: 5, threshold: 100 };
  if (type === "security.block_rate") return { window_min: 5, percent: 30 };
  if (type === "system.container_cpu_gt") return { window_sec: 300, threshold: 80 };
  if (type === "system.host_cpu_gt") return { window_sec: 300, threshold: 85 };
  return {};
}

/** Normalize legacy ``qps`` param to ``threshold`` for list/edit display. */
function normalizeTriggerParams(type: string, params: Record<string, unknown> | null | undefined) {
  const out: Record<string, unknown> = { ...(params || {}) };
  if ((type === "traffic.qps_gt" || type === "traffic.qps_lt") && out.threshold == null && out.qps != null) {
    out.threshold = out.qps;
    delete out.qps;
  }
  return out;
}

const defaultForm = () => ({
  id: null as number | null,
  name: "",
  enabled: true,
  trigger_type: "traffic.baseline_gt",
  trigger_params: { window_sec: 300, percent: 50 } as Record<string, unknown>,
  apply_mode: "suggest_only",
  notify_on: ["trigger", "result"],
  channel_ids: [] as number[],
  cooldown_sec: 300,
  remark: "",
  custom_prompt: "",
});

const form = ref(defaultForm());

function triggerLabel(t: string) {
  return triggers.value.find((x) => x.type === t)?.label || t;
}

function formatTriggerParams(record: any) {
  const meta = triggers.value.find((t) => t.type === record.trigger_type);
  const params = normalizeTriggerParams(record.trigger_type, record.trigger_params);
  if (!meta?.params?.length) return "—";

  const parts: string[] = [];
  for (const p of meta.params) {
    const value = params[p.key];
    if (value == null || value === "") continue;

    let display = String(value);
    if (p.kind === "traffic_window" || p.key === "window_sec") {
      display = trafficWindows.value.find((x) => x.value === Number(value))?.label || `${value} 秒`;
    } else if (p.kind === "system_window") {
      display = systemWindows.value.find((x) => x.value === Number(value))?.label || `${value} 秒`;
    } else if (p.kind === "block_window" || p.key === "window_min") {
      display = blockWindows.value.find((x) => x.value === Number(value))?.label || `${value} 分钟`;
    } else if (p.key === "percent") {
      display = `${value}%`;
    } else if (p.key === "site_scope" || p.kind === "alert_site_scope") {
      if (params.site_scope === "any") {
        display = "任意站点";
      } else if (params.site_scope === "single" || params.site_id != null) {
        display = formatSiteId(Number(params.site_id));
      } else {
        display = "全站";
      }
    } else if (p.key === "site_id") {
      display = formatSiteId(Number(value));
    } else if (p.key === "threshold") {
      display = String(value);
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
  if (tRes.data.traffic_windows?.length) {
    trafficWindows.value = tRes.data.traffic_windows;
  }
  if (tRes.data.block_windows?.length) {
    blockWindows.value = tRes.data.block_windows;
  }
  if (tRes.data.system_windows?.length) {
    systemWindows.value = tRes.data.system_windows;
  }
  channels.value = cRes.data || [];
}

function onTableChange(pag: { current?: number; pageSize?: number }) {
  page.value = pag.current || 1;
  pageSize.value = pag.pageSize || 20;
  load();
}

function openCreate() {
  const type = "traffic.baseline_gt";
  form.value = {
    ...defaultForm(),
    trigger_type: type,
    trigger_params: defaultParamsFor(type),
  };
  modalOpen.value = true;
}

function openEdit(record: any) {
  form.value = {
    ...record,
    trigger_params: normalizeTriggerParams(record.trigger_type, record.trigger_params),
  };
  modalOpen.value = true;
}

async function save() {
  saving.value = true;
  try {
    const payload = { ...form.value };
    delete payload.id;
    payload.trigger_params = normalizeTriggerParams(payload.trigger_type, payload.trigger_params);
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
  line-height: 1.5;
  word-break: break-word;
}
.danger {
  color: #ff4d4f;
}
</style>
