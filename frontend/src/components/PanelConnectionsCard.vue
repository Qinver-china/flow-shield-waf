<template>
  <a-card title="面板集成" style="margin-top: 16px">
    <template #extra>
      <a-button type="primary" size="small" @click="openCreate">添加面板账号</a-button>
    </template>

    <a-alert
      type="info"
      show-icon
      style="margin-bottom: 12px"
      message="添加您搭建网站的面板集成，可以方便地将您的网站及证书导入到流盾 WAF。"
    />

    <fs-data-table
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      size="small"
      api-base="/api/v1/panel-connections"
      :batch="batchConfig"
      has-enabled-column
      :pagination="false"
      @refresh="load"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'provider'">
          {{ providerLabel(record.provider) }}
        </template>
        <template v-else-if="column.key === 'same_server'">
          <a-tag :color="record.same_server ? 'blue' : 'default'">
            {{ record.same_server ? "同服务器" : "远程" }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'api_key'">
          {{ record.has_api_key ? record.api_key_masked : "未填写" }}
        </template>
        <template v-else-if="column.key === 'enabled'">
          <a-tag :color="record.enabled ? 'green' : 'default'">
            {{ record.enabled ? "启用" : "禁用" }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'actions'">
          <a @click="openEdit(record)">编辑</a>
          <a-divider type="vertical" />
          <a @click="testSaved(record)">测连</a>
          <a-divider type="vertical" />
          <a-popconfirm title="确认删除该面板账号？" @confirm="remove(record.id)">
            <a class="danger">删除</a>
          </a-popconfirm>
        </template>
      </template>
    </fs-data-table>

    <fs-form-drawer
      v-model:open="modalOpen"
      title="面板账号"
      :subtitle="form.id ? `#${form.id}` : undefined"
      :mode="form.id ? 'edit' : 'create'"
      :width="640"
      :confirm-loading="saving"
      @ok="save"
    >
      <a-form layout="vertical">
        <fs-form-section title="基本信息">
          <template #extra>
            <form-enabled-switch v-model:checked="form.enabled" />
          </template>
          <a-form-item label="名称" required>
            <a-input v-model:value="form.name" placeholder="例如：本机宝塔" />
          </a-form-item>
          <a-form-item v-if="!form.id" label="面板类型" required>
            <a-select v-model:value="form.provider" @change="onProviderChange">
              <a-select-option value="baota">宝塔</a-select-option>
              <a-select-option value="onepanel">1Panel</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="面板地址" required>
            <a-input
              v-model:value="form.panel_url"
              :placeholder="form.provider === 'baota' ? 'http://172.17.0.1:8888' : 'http://172.17.0.1:10086'"
            />
            <div v-if="form.provider === 'baota'" class="hint">
              填写协议、域名/IP 和端口即可，不必带安全入口
            </div>
          </a-form-item>
          <a-form-item :label="form.id ? 'API 密钥（留空表示不修改）' : 'API 密钥'">
            <a-input-password
              v-model:value="form.api_key"
              :placeholder="form.id ? '留空表示不修改' : '宝塔 API 密钥或 1Panel ApiKey'"
              autocomplete="new-password"
            />
          </a-form-item>
          <a-form-item v-if="form.provider === 'baota'">
            <a-checkbox v-model:checked="form.baota_token_prehashed">
              密钥来自 api.json 的 token（手动添加的请勿勾选）
            </a-checkbox>
          </a-form-item>
          <a-form-item>
            <a-checkbox v-model:checked="form.same_server">同服务器面板</a-checkbox>
            <div class="hint">
              添加的面板与当前流盾 WAF 为同一服务器时勾选
            </div>
          </a-form-item>
          <a-form-item>
            <a-checkbox v-model:checked="form.verify_tls">校验 TLS 证书</a-checkbox>
          </a-form-item>
          <a-form-item label="备注">
            <a-textarea
              v-model:value="form.remark"
              placeholder="可选"
              :auto-size="{ minRows: 1, maxRows: 4 }"
            />
          </a-form-item>
          <a-form-item>
            <a-button :loading="testing" @click="testForm">测试连接</a-button>
          </a-form-item>
        </fs-form-section>
      </a-form>
    </fs-form-drawer>
  </a-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { message } from "ant-design-vue";
import { api } from "@/api";
import FsDataTable from "@/components/FsDataTable.vue";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsFormDrawer from "@/components/FsFormDrawer.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import { commonBatchEditFields } from "@/constants/batch";
import type { BatchConfig } from "@/types/batch";

export interface PanelConnectionRow {
  id: number;
  name: string;
  provider: "baota" | "onepanel";
  panel_url: string;
  same_server: boolean;
  verify_tls: boolean;
  enabled: boolean;
  remark?: string | null;
  extra?: Record<string, unknown>;
  has_api_key: boolean;
  api_key_masked?: string | null;
}

const columns = [
  { title: "名称", dataIndex: "name", key: "name" },
  { title: "类型", key: "provider", width: 100 },
  { title: "地址", dataIndex: "panel_url", key: "panel_url", ellipsis: true },
  { title: "部署", key: "same_server", width: 100 },
  { title: "密钥", key: "api_key", width: 90 },
  { title: "状态", key: "enabled", width: 80 },
  { title: "操作", key: "actions", width: 180 },
];

const batchConfig: BatchConfig = {
  editFields: [commonBatchEditFields.enabled],
};

const rows = ref<PanelConnectionRow[]>([]);
const loading = ref(false);
const modalOpen = ref(false);
const saving = ref(false);
const testing = ref(false);

const emptyForm = () => ({
  id: 0,
  name: "",
  provider: "baota" as "baota" | "onepanel",
  panel_url: "",
  api_key: "",
  same_server: false,
  verify_tls: false,
  enabled: true,
  remark: "",
  baota_token_prehashed: false,
});

const form = reactive(emptyForm());

function providerLabel(provider: string) {
  return provider === "onepanel" ? "1Panel" : "宝塔";
}

function extraPayload() {
  const extra: Record<string, unknown> = {};
  if (form.provider === "baota" && form.baota_token_prehashed) {
    extra.baota_token_prehashed = true;
  }
  return extra;
}

function onProviderChange() {
  if (!form.id) {
    form.name = form.provider === "baota" ? "本机宝塔" : "本机 1Panel";
  }
}

function openCreate() {
  Object.assign(form, emptyForm());
  modalOpen.value = true;
}

function openEdit(record: PanelConnectionRow) {
  Object.assign(form, {
    id: record.id,
    name: record.name,
    provider: record.provider,
    panel_url: record.panel_url,
    api_key: "",
    same_server: !!record.same_server,
    verify_tls: !!record.verify_tls,
    enabled: record.enabled !== false,
    remark: record.remark || "",
    baota_token_prehashed: !!(record.extra && record.extra.baota_token_prehashed),
  });
  modalOpen.value = true;
}

async function load() {
  loading.value = true;
  try {
    const resp = await api.get<PanelConnectionRow[]>("/api/v1/panel-connections");
    rows.value = resp.data || [];
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!form.name.trim() || !form.panel_url.trim()) {
    message.warning("请填写名称和面板地址");
    return;
  }
  saving.value = true;
  try {
    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      panel_url: form.panel_url.trim(),
      same_server: form.same_server,
      verify_tls: form.verify_tls,
      enabled: form.enabled,
      remark: form.remark || null,
      extra: extraPayload(),
    };
    if (form.id) {
      if (form.api_key.trim()) payload.api_key = form.api_key.trim();
      await api.put(`/api/v1/panel-connections/${form.id}`, payload);
      message.success("已保存");
    } else {
      payload.provider = form.provider;
      payload.api_key = form.api_key.trim();
      await api.post("/api/v1/panel-connections", payload);
      message.success("已添加");
    }
    modalOpen.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}

async function remove(id: number) {
  await api.del(`/api/v1/panel-connections/${id}`);
  message.success("已删除");
  await load();
}

async function testSaved(record: PanelConnectionRow) {
  const resp = await api.post(`/api/v1/panel-connections/${record.id}/test`, {}, { timeout: 30000 });
  message.success(resp.data?.message || "连接成功");
}

async function testForm() {
  if (!form.panel_url.trim()) {
    message.warning("请先填写面板地址");
    return;
  }
  testing.value = true;
  try {
    const body = {
      provider: form.provider,
      panel_url: form.panel_url.trim(),
      api_key: form.api_key.trim() || undefined,
      verify_tls: form.verify_tls,
      extra: extraPayload(),
    };
    const url = form.id
      ? `/api/v1/panel-connections/${form.id}/test`
      : "/api/v1/panel-connections/test";
    const resp = await api.post(url, body, { timeout: 30000 });
    message.success(resp.data?.message || "连接成功");
  } finally {
    testing.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.danger {
  color: var(--fs-danger, #ef4444);
}
.hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--fs-text-secondary);
  line-height: 1.5;
}
</style>
