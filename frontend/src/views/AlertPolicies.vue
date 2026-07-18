<template>
  <page-shell title="预警通知" description="配置流量与拦截阈值告警，通过通知通道提醒管理员">
    <template #actions>
      <a-button type="primary" @click="openCreate">新增预警规则</a-button>
    </template>

    <a-alert
      type="info"
      show-icon
      style="margin-bottom: 16px"
      message="当满足下方条件时，系统将通过所选通知通道提醒管理员。建议优先配置「流量高于基线」与「拦截次数超过阈值」组合。"
    />

    <fs-data-table
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="pagination"
      api-base="/api/v1/alert-policies"
      :batch="batchConfig"
      has-enabled-column
      :scroll="{ x: 900 }"
      @change="onTableChange"
      @refresh="load"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'condition'">
          <div>{{ conditionLabel(record.condition_type) }}</div>
          <div class="sub">{{ formatParams(record) }}</div>
        </template>
        <template v-else-if="column.key === 'channels'">
          {{ formatChannels(record.channel_ids) }}
        </template>
        <template v-else-if="column.key === 'enabled'">
          <a-switch
            :checked="record.enabled"
            @change="(v: boolean) => toggleEnabled(record, v)"
          />
        </template>
        <template v-else-if="column.key === 'last_fired_at'">
          <template v-if="record.last_fired_at">
            <div>{{ formatDateTime(record.last_fired_at) }}</div>
            <a-tag
              v-if="record.last_dispatch_status === 'failed'"
              color="error"
              style="margin-top: 4px"
            >
              发送失败
            </a-tag>
            <a-tag
              v-else-if="record.last_dispatch_status === 'sent'"
              color="success"
              style="margin-top: 4px"
            >
              已发送
            </a-tag>
          </template>
          <template v-else>从未触发</template>
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

    <a-card title="最近通知记录" class="fs-card" style="margin-top: 16px" size="small">
      <a-table
        :columns="logColumns"
        :data-source="logs"
        :loading="logsLoading"
        row-key="id"
        size="small"
        :pagination="{ pageSize: 10 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'created_at'">
            {{ formatDateTime(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="record.status === 'sent' ? 'green' : 'red'">{{ record.status }}</a-tag>
          </template>
          <template v-else-if="column.key === 'detail'">
            {{ record.detail || "—" }}
          </template>
        </template>
      </a-table>
    </a-card>

    <fs-form-drawer
      v-model:open="modalOpen"
      title="预警规则"
      :subtitle="form.id ? `#${form.id}` : undefined"
      :mode="form.id ? 'edit' : 'create'"
      :width="720"
      :confirm-loading="saving"
      @ok="save"
    >
      <a-form layout="vertical">
        <fs-form-section title="基本信息">
          <template #extra>
            <form-enabled-switch v-model:checked="form.enabled" />
          </template>
          <a-form-item label="规则名称" required>
            <a-input v-model:value="form.name" placeholder="例如：流量突增邮件告警" />
          </a-form-item>
          <a-form-item label="备注">
            <a-input v-model:value="form.remark" placeholder="可选" />
          </a-form-item>
        </fs-form-section>

        <fs-form-section title="触发条件" description="选择预警类型并配置阈值参数">
          <a-form-item label="预警条件" required>
            <a-select v-model:value="form.condition_type" @change="onConditionChange">
              <a-select-opt-group
                v-for="group in conditionGroups"
                :key="group.name"
                :label="group.name"
              >
                <a-select-option v-for="c in group.items" :key="c.type" :value="c.type">
                  {{ c.label }}
                </a-select-option>
              </a-select-opt-group>
            </a-select>
            <p v-if="selectedCondition?.description" class="fs-hint is-inline">
              {{ selectedCondition.description }}
            </p>
          </a-form-item>

          <a-row v-if="selectedCondition?.params?.length" :gutter="16">
            <a-col v-for="p in selectedCondition.params" :key="p.key" :span="12">
              <a-form-item :label="p.label" :required="p.required !== false">
                <a-select
                  v-if="p.kind === 'traffic_window'"
                  v-model:value="form.condition_params[p.key]"
                >
                  <a-select-option
                    v-for="w in trafficWindows"
                    :key="w.value"
                    :value="w.value"
                  >{{ w.label }}</a-select-option>
                </a-select>
                <a-select
                  v-else-if="p.kind === 'block_window'"
                  v-model:value="form.condition_params[p.key]"
                >
                  <a-select-option
                    v-for="w in blockWindows"
                    :key="w.value"
                    :value="w.value"
                  >{{ w.label }}</a-select-option>
                </a-select>
                <a-input-number
                  v-else-if="p.kind === 'number'"
                  v-model:value="form.condition_params[p.key]"
                  :min="p.min ?? 0"
                  :max="p.max"
                  style="width: 100%"
                />
                <site-single-select
                  v-else-if="p.kind === 'site_id'"
                  v-model:value="form.condition_params[p.key]"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </fs-form-section>

        <fs-form-section title="通知设置">
          <a-form-item label="通知通道" required>
            <a-select
              v-model:value="form.channel_ids"
              mode="multiple"
              placeholder="选择已配置的通知通道"
              option-filter-prop="label"
            >
              <a-select-option
                v-for="ch in channels"
                :key="ch.id"
                :value="ch.id"
                :label="ch.name"
                :disabled="!ch.enabled"
              >
                {{ ch.name }}（{{ channelTypeLabel(ch.channel_type) }}）
              </a-select-option>
            </a-select>
            <p class="fs-hint is-inline">请先在「系统设置 → 通知通道」中配置邮件等通道。</p>
          </a-form-item>

          <a-form-item label="冷却时间（秒）">
            <a-input-number v-model:value="form.cooldown_sec" :min="60" :max="86400" style="width: 200px" />
            <p class="fs-hint is-inline">同一规则触发后在此时间内不重复通知</p>
          </a-form-item>
        </fs-form-section>
      </a-form>
    </fs-form-drawer>
  </page-shell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { message } from "ant-design-vue";
import { api } from "@/api";
import FsDataTable from "@/components/FsDataTable.vue";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsFormDrawer from "@/components/FsFormDrawer.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import PageShell from "@/components/PageShell.vue";
import SiteSingleSelect from "@/components/SiteSingleSelect.vue";
import { commonBatchEditFields } from "@/constants/batch";
import { useSiteOptions } from "@/composables/useSiteOptions";
import { formatDateTime } from "@/utils/datetime";
import type { BatchConfig } from "@/types/batch";

const { formatSiteId } = useSiteOptions();

const columns = [
  { title: "名称", dataIndex: "name", key: "name" },
  { title: "预警条件", key: "condition", width: 280 },
  { title: "通知通道", key: "channels", width: 160 },
  { title: "冷却(s)", dataIndex: "cooldown_sec", width: 90 },
  { title: "上次触发", key: "last_fired_at", width: 170 },
  { title: "启用", key: "enabled", width: 70 },
  { title: "操作", key: "actions", width: 120 },
];

const logColumns = [
  { title: "时间", dataIndex: "created_at", width: 170 },
  { title: "状态", key: "status", width: 80 },
  { title: "内容", dataIndex: "message", ellipsis: true },
  { title: "详情", key: "detail", width: 220, ellipsis: true },
];

const batchConfig: BatchConfig = {
  editFields: [commonBatchEditFields.enabled],
};

const rows = ref<any[]>([]);
const logs = ref<any[]>([]);
const channels = ref<any[]>([]);
const conditions = ref<any[]>([]);
const channelTypes = ref<any[]>([]);
const trafficWindows = ref([
  { value: 60, label: "1 分钟" },
  { value: 300, label: "5 分钟" },
  { value: 1800, label: "30 分钟" },
  { value: 3600, label: "60 分钟" },
]);
const blockWindows = ref([{ value: 5, label: "5 分钟" }, { value: 15, label: "15 分钟" }, { value: 30, label: "30 分钟" }, { value: 60, label: "60 分钟" }]);

const loading = ref(false);
const logsLoading = ref(false);
const modalOpen = ref(false);
const saving = ref(false);
const pagination = reactive({ current: 1, pageSize: 20, total: 0 });

const form = reactive<any>({
  id: 0,
  name: "",
  enabled: true,
  condition_type: "traffic.baseline_gt",
  condition_params: { window_sec: 300, percent: 50 },
  channel_ids: [] as number[],
  cooldown_sec: 300,
  remark: "",
});

const conditionGroups = computed(() => {
  const map: Record<string, any[]> = {};
  for (const c of conditions.value) {
    map[c.category] = map[c.category] || [];
    map[c.category].push(c);
  }
  return Object.entries(map).map(([name, items]) => ({ name, items }));
});

const selectedCondition = computed(() =>
  conditions.value.find((c) => c.type === form.condition_type),
);

function conditionLabel(type: string) {
  return conditions.value.find((c) => c.type === type)?.label || type;
}

function channelTypeLabel(type: string) {
  return channelTypes.value.find((t) => t.value === type)?.label || type;
}

function formatChannels(ids: number[]) {
  if (!ids?.length) return "-";
  return ids
    .map((id) => channels.value.find((c) => c.id === id)?.name || `#${id}`)
    .join("、");
}

function formatParams(record: any) {
  const p = record.condition_params || {};
  const parts: string[] = [];
  if (p.window_sec) {
    const w = trafficWindows.value.find((x) => x.value === p.window_sec);
    parts.push(w?.label || `${p.window_sec}s`);
  }
  if (p.window_min) {
    const w = blockWindows.value.find((x) => x.value === p.window_min);
    parts.push(w?.label || `${p.window_min}min`);
  }
  if (p.percent != null) parts.push(`${p.percent}%`);
  if (p.threshold != null) parts.push(`阈值 ${p.threshold}`);
  if (p.site_id != null) parts.push(formatSiteId(p.site_id));
  return parts.join(" · ") || "—";
}

function defaultParamsFor(type: string) {
  if (type === "traffic.burst_logging") return {};
  if (type.startsWith("traffic.baseline")) return { window_sec: 300, percent: 50 };
  if (type.startsWith("traffic.abs")) return { window_sec: 300, threshold: 1000 };
  if (type.startsWith("traffic.qps")) return { window_sec: 60, threshold: 100 };
  if (type === "security.block_count") return { window_min: 5, threshold: 100 };
  if (type === "security.block_rate") return { window_min: 5, percent: 30 };
  return {};
}

function onConditionChange() {
  form.condition_params = defaultParamsFor(form.condition_type);
}

function openCreate() {
  Object.assign(form, {
    id: 0,
    name: "",
    enabled: true,
    condition_type: "traffic.baseline_gt",
    condition_params: defaultParamsFor("traffic.baseline_gt"),
    channel_ids: [],
    cooldown_sec: 300,
    remark: "",
  });
  modalOpen.value = true;
}

function openEdit(record: any) {
  Object.assign(form, {
    id: record.id,
    name: record.name,
    enabled: record.enabled,
    condition_type: record.condition_type,
    condition_params: { ...record.condition_params },
    channel_ids: [...(record.channel_ids || [])],
    cooldown_sec: record.cooldown_sec,
    remark: record.remark || "",
  });
  modalOpen.value = true;
}

async function loadMeta() {
  const [metaResp, chResp] = await Promise.all([
    api.get("/api/v1/alert-policies/meta/conditions"),
    api.get("/api/v1/notification-channels"),
  ]);
  conditions.value = metaResp.data.conditions || [];
  channelTypes.value = metaResp.data.channel_types || [];
  if (metaResp.data.traffic_windows?.length) {
    trafficWindows.value = metaResp.data.traffic_windows;
  }
  channels.value = chResp.data || [];
}

async function load() {
  loading.value = true;
  try {
    const resp = await api.get("/api/v1/alert-policies", {
      page: pagination.current,
      page_size: pagination.pageSize,
    });
    rows.value = resp.data.items || [];
    pagination.total = resp.data.total || 0;
  } finally {
    loading.value = false;
  }
}

async function loadLogs() {
  logsLoading.value = true;
  try {
    const resp = await api.get("/api/v1/alert-policies/logs", { limit: 50 });
    logs.value = resp.data || [];
  } finally {
    logsLoading.value = false;
  }
}

function onTableChange(pag: any) {
  pagination.current = pag.current;
  pagination.pageSize = pag.pageSize;
  load();
}

async function save() {
  if (!form.name?.trim()) {
    message.error("请填写规则名称");
    return;
  }
  if (!form.channel_ids?.length) {
    message.error("请至少选择一个通知通道");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: form.name,
      enabled: form.enabled,
      condition_type: form.condition_type,
      condition_params: { ...form.condition_params },
      channel_ids: form.channel_ids,
      cooldown_sec: form.cooldown_sec,
      remark: form.remark || null,
    };
    if (form.id) {
      await api.put(`/api/v1/alert-policies/${form.id}`, payload);
    } else {
      await api.post("/api/v1/alert-policies", payload);
    }
    message.success("已保存");
    modalOpen.value = false;
    await load();
  } catch (e: any) {
    if (e?.response?.status !== 401) {
      // interceptor already surfaced the error toast
    }
  } finally {
    saving.value = false;
  }
}

async function toggleEnabled(record: any, enabled: boolean) {
  const prev = record.enabled;
  record.enabled = enabled;
  try {
    await api.put(`/api/v1/alert-policies/${record.id}`, { enabled });
  } catch {
    record.enabled = prev;
  }
}

async function remove(id: number) {
  await api.del(`/api/v1/alert-policies/${id}`);
  message.success("已删除");
  await load();
}

onMounted(async () => {
  await loadMeta();
  await load();
  await loadLogs();
});
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.toolbar h3 {
  margin: 0;
}
.sub {
  color: #64748b;
  font-size: 12px;
}
.danger {
  color: #ef4444;
}
</style>
