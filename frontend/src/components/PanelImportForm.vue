<template>
  <a-spin :spinning="loading">
    <a-empty v-if="!tabConnections.length" class="panel-import-empty" :description="emptyDescription">
      <a-button type="primary" @click="goPanelSettings">去添加</a-button>
    </a-empty>

    <template v-else>
      <fs-form-section title="选择面板" v-if="tabConnections.length > 1">
        <a-form-item>
          <a-select :value="connectionId" style="width: 100%" :options="accountOptions" @change="onAccountChange" />
        </a-form-item>
      </fs-form-section>

      <fs-form-section :title="kind === 'sites' ? '选择站点' : '选择证书'">
        <a-table size="small" row-key="key" :columns="tableColumns" :data-source="items" :pagination="false"
          :row-selection="rowSelection" :scroll="{ y: 420 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'domains'">
              {{ (record.domains || []).join("、") || "-" }}
            </template>
            <template v-else-if="column.key === 'ssl'">
              {{ record.has_ssl ? (record.ssl_not_after || "已部署") : "无" }}
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag v-if="record.already_imported || record.skip_reason" color="default">
                {{ record.skip_reason || "已存在" }}
              </a-tag>
              <a-tag v-else color="green">可导入</a-tag>
            </template>
          </template>
        </a-table>
      </fs-form-section>

      <fs-form-section v-if="kind === 'sites'" title="回源地址" description="默认为面板地址，如需自定义可在下方修改">
        <a-form-item>
          <origin-host-input v-model:value="originHost" />
        </a-form-item>
      </fs-form-section>

      <a-alert v-if="kind === 'sites' && connection?.same_server" type="info" show-icon
          style="margin-bottom: 12px" message="同服务器导入：回源默认 host.docker.internal，80/443 会纠正为 8080/4343，并关闭内容缓冲。" />
    </template>
  </a-spin>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { message } from "ant-design-vue";
import { api } from "@/api";
import FsFormSection from "@/components/FsFormSection.vue";
import OriginHostInput from "@/components/OriginHostInput.vue";
import type { PanelConnectionRow } from "@/components/PanelConnectionsCard.vue";

export type PanelImportKind = "sites" | "certificates";
export type PanelProvider = "baota" | "onepanel";

export interface PanelImportStatus {
  canImport: boolean;
  okText: string;
  importing: boolean;
  loading: boolean;
}

interface PreviewItem {
  key: string;
  name: string;
  domains: string[];
  origin_http_port?: number;
  origin_https_port?: number;
  has_ssl?: boolean;
  ssl_not_after?: string | null;
  not_after?: string | null;
  already_imported?: boolean;
  skip_reason?: string | null;
}

const props = defineProps<{
  kind: PanelImportKind;
  provider: PanelProvider;
}>();

const emit = defineEmits<{
  imported: [];
  close: [];
  status: [status: PanelImportStatus];
}>();

const router = useRouter();
const loading = ref(false);
const importing = ref(false);
const items = ref<PreviewItem[]>([]);
const selectedKeys = ref<string[]>([]);
const originHost = ref("host.docker.internal");
const connections = ref<PanelConnectionRow[]>([]);
const connectionId = ref<number | null>(null);

const emptyDescription = computed(() =>
  props.provider === "baota" ? "暂未添加宝塔账号" : "暂未添加 1Panel 账号",
);

const tabConnections = computed(() =>
  connections.value.filter((item) => item.provider === props.provider && item.enabled),
);

const connection = computed(
  () => tabConnections.value.find((item) => item.id === connectionId.value) || null,
);

const canImport = computed(() => !!connection.value);

const accountOptions = computed(() =>
  tabConnections.value.map((item) => ({ value: item.id, label: item.name })),
);

const okText = computed(() =>
  selectedKeys.value.length ? `导入 ${selectedKeys.value.length} 项` : "导入",
);

const tableColumns = computed(() => {
  if (props.kind === "sites") {
    return [
      { title: "站点", dataIndex: "name", key: "name", width: 160 },
      { title: "域名", key: "domains", ellipsis: true },
      { title: "回源端口", key: "ports", width: 110, customRender: ({ record }: { record: PreviewItem }) => `${record.origin_http_port}/${record.origin_https_port}` },
      { title: "证书", key: "ssl", width: 140 },
      { title: "状态", key: "status", width: 180 },
    ];
  }
  return [
    { title: "证书", dataIndex: "name", key: "name", width: 180 },
    { title: "域名", key: "domains", ellipsis: true },
    { title: "到期", dataIndex: "not_after", key: "not_after", width: 160 },
    { title: "状态", key: "status", width: 180 },
  ];
});

const selectableKeys = computed(() =>
  items.value.filter((item) => !item.already_imported && !item.skip_reason).map((item) => item.key),
);

const rowSelection = computed(() => ({
  selectedRowKeys: selectedKeys.value,
  onChange: (keys: (string | number)[]) => {
    selectedKeys.value = keys.map(String);
  },
  getCheckboxProps: (record: PreviewItem) => ({
    disabled: !!(record.already_imported || record.skip_reason),
  }),
}));

function pickFirstAccount() {
  connectionId.value = tabConnections.value[0]?.id ?? null;
}

function clearPreview() {
  items.value = [];
  selectedKeys.value = [];
}

function emitStatus() {
  emit("status", {
    canImport: canImport.value,
    okText: okText.value,
    importing: importing.value,
    loading: loading.value,
  });
}

async function loadConnections() {
  try {
    const resp = await api.get<PanelConnectionRow[]>("/api/v1/panel-connections");
    connections.value = resp.data || [];
  } catch {
    connections.value = [];
  }
}

async function loadPreview() {
  if (!connection.value) {
    clearPreview();
    return;
  }
  loading.value = true;
  clearPreview();
  try {
    const path =
      props.kind === "sites"
        ? `/api/v1/panel-connections/${connection.value.id}/sites`
        : `/api/v1/panel-connections/${connection.value.id}/certificates`;
    const resp = await api.get<{
      origin_host?: string;
      items: PreviewItem[];
    }>(path, undefined, { timeout: 120000 });
    items.value = resp.data?.items || [];
    if (props.kind === "sites") {
      originHost.value = resp.data?.origin_host || originHost.value;
    }
    selectedKeys.value = selectableKeys.value;
  } finally {
    loading.value = false;
  }
}

async function applyTab() {
  pickFirstAccount();
  if (connection.value) {
    await loadPreview();
  } else {
    clearPreview();
  }
}

async function bootstrap() {
  loading.value = true;
  connectionId.value = null;
  clearPreview();
  try {
    await loadConnections();
    await applyTab();
  } finally {
    if (!connection.value) loading.value = false;
  }
}

function onAccountChange(id: number) {
  connectionId.value = id;
  void loadPreview();
}

function goPanelSettings() {
  emit("close");
  router.push({ path: "/settings", query: { tab: "panels" } });
}

async function submit() {
  if (!connection.value) return;
  if (!selectedKeys.value.length) {
    message.warning("请选择要导入的项目");
    return;
  }
  importing.value = true;
  try {
    const path =
      props.kind === "sites"
        ? `/api/v1/panel-connections/${connection.value.id}/sites/import`
        : `/api/v1/panel-connections/${connection.value.id}/certificates/import`;
    const payload: Record<string, unknown> = { keys: selectedKeys.value };
    if (props.kind === "sites") {
      payload.origin_host = originHost.value;
    }
    const resp = await api.post(path, payload, { timeout: 120000 });
    const data = resp.data || {};
    const imported = (data.imported || []).length;
    const skipped = (data.skipped || []).length;
    const failed = (data.failed || []).length;
    const parts = [`已导入 ${imported}`];
    if (skipped) parts.push(`跳过 ${skipped}`);
    if (failed) parts.push(`失败 ${failed}`);
    if (data.warning) {
      message.warning(`${parts.join("，")}。${data.warning}`);
    } else {
      message.success(parts.join("，"));
    }
    emit("imported");
  } finally {
    importing.value = false;
  }
}

watch([canImport, okText, importing, loading], emitStatus, { immediate: true });

onMounted(() => {
  void bootstrap();
});

defineExpose({ submit });
</script>

<style scoped>
.panel-import-empty {
  padding: 48px 0 24px;
}
</style>
