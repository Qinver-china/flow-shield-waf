<template>
  <a-card title="通知通道" style="margin-top: 16px">
    <template #extra>
      <a-button type="primary" size="small" @click="openCreate">增加通知通道</a-button>
    </template>

    <fs-data-table
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      size="small"
      api-base="/api/v1/notification-channels"
      :batch="batchConfig"
      has-enabled-column
      :pagination="false"
      @refresh="load"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'channel_type'">
          {{ channelLabel(record.channel_type) }}
          <a-tag v-if="!isImplemented(record.channel_type)" color="default" style="margin-left: 6px">
            即将支持
          </a-tag>
        </template>
        <template v-else-if="column.key === 'enabled'">
          <a-tag :color="record.enabled ? 'green' : 'default'">
            {{ record.enabled ? "启用" : "禁用" }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'recipients'">
          {{ formatRecipients(record) }}
        </template>
        <template v-else-if="column.key === 'actions'">
          <a @click="openEdit(record)">编辑</a>
          <a-divider type="vertical" />
          <a
            v-if="record.channel_type === 'email' && record.enabled"
            @click="testChannel(record.id)"
          >测试</a>
          <a-divider v-if="record.channel_type === 'email' && record.enabled" type="vertical" />
          <a-popconfirm title="确认删除该通道？" @confirm="remove(record.id)">
            <a class="danger">删除</a>
          </a-popconfirm>
        </template>
      </template>
    </fs-data-table>

    <fs-form-drawer
      v-model:open="modalOpen"
      title="通知通道"
      :subtitle="form.id ? `#${form.id}` : undefined"
      :mode="form.id ? 'edit' : 'create'"
      :width="680"
      :confirm-loading="saving"
      @ok="save"
    >
      <a-form layout="vertical">
        <fs-form-section title="基本信息">
          <template #extra>
            <form-enabled-switch v-model:checked="form.enabled" />
          </template>
          <a-form-item label="通道名称" required>
            <a-input v-model:value="form.name" placeholder="例如：运维邮件组" />
          </a-form-item>
          <a-form-item v-if="!form.id" label="通道类型" required>
            <a-select v-model:value="form.channel_type" @change="onTypeChange">
              <a-select-option
                v-for="t in channelTypes"
                :key="t.value"
                :value="t.value"
                :disabled="!t.implemented"
              >
                {{ t.label }}{{ t.implemented ? "" : "（预留）" }}
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="备注">
            <a-input v-model:value="form.remark" placeholder="可选" />
          </a-form-item>
        </fs-form-section>

        <fs-form-section
          v-if="form.channel_type === 'email'"
          title="SMTP 邮件配置"
          description="用于发送预警与系统通知邮件"
        >
          <a-row :gutter="16">
            <a-col :span="16">
              <a-form-item label="SMTP 服务器" required>
                <a-input v-model:value="form.config.smtp_host" placeholder="smtp.example.com" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="端口" required>
                <a-input-number v-model:value="form.config.smtp_port" :min="1" :max="65535" style="width: 100%" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="加密方式">
            <a-select v-model:value="form.config.smtp_security">
              <a-select-option value="ssl">SSL（465）</a-select-option>
              <a-select-option value="starttls">STARTTLS（587）</a-select-option>
              <a-select-option value="plain">无加密</a-select-option>
            </a-select>
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="SMTP 用户名">
                <a-input v-model:value="form.config.smtp_user" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="SMTP 密码">
                <a-input-password
                  v-model:value="form.config.smtp_password"
                  placeholder="留空表示不修改"
                  autocomplete="new-password"
                />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="发件人邮箱" required>
                <a-input v-model:value="form.config.from_address" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="发件人名称">
                <a-input v-model:value="form.config.from_name" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="收件人（可多个）" required>
            <a-select
              v-model:value="form.config.to_addresses"
              mode="tags"
              placeholder="输入邮箱后回车"
              autocomplete="off"
              :token-separators="[',']"
              @change="onRecipientsChange"
            />
          </a-form-item>
        </fs-form-section>

        <fs-form-section v-else title="通道配置">
          <a-alert type="info" show-icon message="该通道类型尚未开放，敬请期待后续版本。" />
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

interface ChannelType {
  value: string;
  label: string;
  implemented: boolean;
}

const columns = [
  { title: "名称", dataIndex: "name", key: "name" },
  { title: "类型", key: "channel_type", width: 140 },
  { title: "收件人/目标", key: "recipients", ellipsis: true },
  { title: "状态", key: "enabled", width: 80 },
  { title: "操作", key: "actions", width: 180 },
];

const batchConfig: BatchConfig = {
  editFields: [commonBatchEditFields.enabled],
};

const rows = ref<any[]>([]);
const loading = ref(false);
const modalOpen = ref(false);
const saving = ref(false);
const channelTypes = ref<ChannelType[]>([]);

const emptyEmailConfig = () => ({
  smtp_host: "",
  smtp_port: 465,
  smtp_security: "ssl",
  smtp_user: "",
  smtp_password: "",
  from_address: "",
  from_name: "流盾WAF",
  to_addresses: [] as string[],
});

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function normalizeRecipients(addresses: unknown): string[] {
  const list = Array.isArray(addresses) ? addresses : [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of list) {
    const item = String(raw || "").trim();
    if (!EMAIL_RE.test(item)) continue;
    const key = item.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}

function onRecipientsChange(value: string[]) {
  form.config.to_addresses = normalizeRecipients(value);
}

const form = reactive<any>({
  id: 0,
  name: "",
  channel_type: "email",
  enabled: true,
  remark: "",
  config: emptyEmailConfig(),
});

function channelLabel(type: string) {
  return channelTypes.value.find((t) => t.value === type)?.label || type;
}

function isImplemented(type: string) {
  return channelTypes.value.find((t) => t.value === type)?.implemented ?? false;
}

function formatRecipients(record: any) {
  if (record.channel_type === "email") {
    const list = normalizeRecipients(record.config?.to_addresses || []);
    return list.join(", ") || "-";
  }
  return "-";
}

function onTypeChange() {
  if (form.channel_type === "email") {
    form.config = emptyEmailConfig();
  }
}

function openCreate() {
  Object.assign(form, {
    id: 0,
    name: "",
    channel_type: "email",
    enabled: true,
    remark: "",
    config: emptyEmailConfig(),
  });
  modalOpen.value = true;
}

function openEdit(record: any) {
  Object.assign(form, {
    id: record.id,
    name: record.name,
    channel_type: record.channel_type,
    enabled: record.enabled,
    remark: record.remark || "",
    config: {
      ...emptyEmailConfig(),
      ...(record.config || {}),
      smtp_password: "",
      to_addresses: normalizeRecipients(record.config?.to_addresses),
    },
  });
  modalOpen.value = true;
}

async function load() {
  loading.value = true;
  try {
    const [listResp, metaResp] = await Promise.all([
      api.get("/api/v1/notification-channels"),
      api.get("/api/v1/alert-policies/meta/conditions"),
    ]);
    rows.value = listResp.data || [];
    channelTypes.value = metaResp.data.channel_types || [];
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!form.name?.trim()) {
    message.error("请填写通道名称");
    return;
  }
  if (form.channel_type === "email") {
    form.config.to_addresses = normalizeRecipients(form.config.to_addresses);
    if (!form.config.smtp_host || !form.config.from_address || !form.config.to_addresses.length) {
      message.error("请完善 SMTP 与收件人配置");
      return;
    }
  }
  saving.value = true;
  try {
    const payload = {
      name: form.name,
      channel_type: form.channel_type,
      enabled: form.enabled,
      remark: form.remark || null,
      config: { ...form.config },
    };
    if (form.id) {
      if (!payload.config.smtp_password) delete payload.config.smtp_password;
      await api.put(`/api/v1/notification-channels/${form.id}`, payload);
    } else {
      await api.post("/api/v1/notification-channels", payload);
    }
    message.success("已保存");
    modalOpen.value = false;
    await load();
  } catch (e: any) {
    message.error(e?.response?.data?.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function remove(id: number) {
  await api.del(`/api/v1/notification-channels/${id}`);
  message.success("已删除");
  await load();
}

async function testChannel(id: number) {
  try {
    await api.post(`/api/v1/notification-channels/${id}/test`);
    message.success("测试邮件已发送");
  } catch (e: any) {
    message.error(e?.response?.data?.message || "发送失败");
  }
}

onMounted(load);
</script>

<style scoped>
.danger {
  color: #ef4444;
}
</style>
