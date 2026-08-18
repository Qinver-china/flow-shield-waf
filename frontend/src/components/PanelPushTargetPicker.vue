<template>
  <a-spin :spinning="loading">
    <a-empty v-if="!tabConnections.length" class="panel-push-empty" :description="emptyDescription">
      <a-button type="primary" @click="goPanelSettings">去添加</a-button>
    </a-empty>

    <template v-else>
      <a-form-item label="选择面板" required>
        <a-select :value="connectionId" style="width: 100%" :options="accountOptions" placeholder="选择已保存的面板账号"
          @change="onAccountChange" />
      </a-form-item>
      <a-form-item label="同步站点" required>
        <a-table v-if="connectionId" size="small" row-key="key" :columns="tableColumns" :data-source="items"
          :pagination="false" :row-selection="rowSelection" :scroll="{ y: 240 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'domains'">
              {{ (record.domains || []).join("、") || "-" }}
            </template>
            <template v-else-if="column.key === 'ssl'">
              {{ record.has_ssl ? (record.ssl_not_after || "已部署") : "无" }}
            </template>
          </template>
        </a-table>
        <p v-else class="fs-hint">请先选择面板账号。</p>
      </a-form-item>
    </template>
  </a-spin>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/api";
import type { PanelConnectionRow } from "@/components/PanelConnectionsCard.vue";
import type { PanelProvider } from "@/components/PanelImportForm.vue";

interface PreviewItem {
  key: string;
  name: string;
  domains: string[];
  has_ssl?: boolean;
  ssl_not_after?: string | null;
  skip_reason?: string | null;
}

const props = defineProps<{
  provider: PanelProvider;
  connectionId: number | null;
  siteKeys: string[];
  certDomains?: string[];
}>();

const emit = defineEmits<{
  "update:connectionId": [id: number | null];
  "update:siteKeys": [keys: string[]];
  close: [];
}>();

const router = useRouter();
const loading = ref(false);
const items = ref<PreviewItem[]>([]);
const connections = ref<PanelConnectionRow[]>([]);

const emptyDescription = computed(() =>
  props.provider === "baota" ? "暂未添加宝塔账号" : "暂未添加 1Panel 账号",
);

const tabConnections = computed(() =>
  connections.value.filter((item) => item.provider === props.provider && item.enabled),
);

const accountOptions = computed(() =>
  tabConnections.value.map((item) => ({ value: item.id, label: item.name })),
);

const tableColumns = [
  { title: "站点", dataIndex: "name", key: "name", width: 140 },
  { title: "域名", key: "domains" },
  { title: "证书", key: "ssl", width: 120 },
];

const selectableKeys = computed(() =>
  items.value.filter((item) => !item.skip_reason).map((item) => item.key),
);

const rowSelection = computed(() => ({
  selectedRowKeys: props.siteKeys,
  onChange: (keys: (string | number)[]) => {
    emit(
      "update:siteKeys",
      keys.map(String).filter((key) => selectableKeys.value.includes(key)),
    );
  },
  getCheckboxProps: (record: PreviewItem) => ({
    disabled: !!record.skip_reason,
  }),
}));

function goPanelSettings() {
  emit("close");
  router.push({ path: "/settings", query: { tab: "panels" } });
}

function onAccountChange(id: number) {
  emit("update:connectionId", id);
  emit("update:siteKeys", []);
}

async function loadConnections() {
  try {
    const resp = await api.get<PanelConnectionRow[]>("/api/v1/panel-connections");
    connections.value = resp.data || [];
  } catch {
    connections.value = [];
  }
}

function normalizeDomain(value: string) {
  return value.trim().toLowerCase().replace(/\.$/, "");
}

/** True when every panel-site domain is covered by the certificate SAN list. */
function siteCoveredByCert(siteDomains: string[], certDomains: string[]) {
  const cert = new Set(certDomains.map(normalizeDomain).filter(Boolean));
  if (!cert.size) return false;
  const domains = siteDomains.map(normalizeDomain).filter(Boolean);
  if (!domains.length) return false;
  return domains.every((domain) => cert.has(domain));
}

function suggestedSiteKeys(list: PreviewItem[]) {
  const certDomains = props.certDomains || [];
  return list
    .filter((item) => !item.skip_reason && siteCoveredByCert(item.domains || [], certDomains))
    .map((item) => item.key);
}

async function loadPreview() {
  if (!props.connectionId || !tabConnections.value.some((item) => item.id === props.connectionId)) {
    items.value = [];
    return;
  }
  const shouldSuggest = props.siteKeys.length === 0;
  loading.value = true;
  try {
    const resp = await api.get<{ items: PreviewItem[] }>(
      `/api/v1/panel-connections/${props.connectionId}/sites`,
      { purpose: "sync" },
      { timeout: 120000 },
    );
    items.value = resp.data?.items || [];
    if (shouldSuggest) {
      const matched = suggestedSiteKeys(items.value);
      if (matched.length) emit("update:siteKeys", matched);
    }
  } finally {
    loading.value = false;
  }
}

async function bootstrap() {
  loading.value = true;
  items.value = [];
  try {
    await loadConnections();
    const current = tabConnections.value.find((item) => item.id === props.connectionId);
    if (!current) {
      const firstId = tabConnections.value[0]?.id ?? null;
      if (firstId !== props.connectionId) {
        emit("update:connectionId", firstId);
      }
      emit("update:siteKeys", []);
    }
    if (props.connectionId && tabConnections.value.some((item) => item.id === props.connectionId)) {
      await loadPreview();
    }
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.provider,
  () => {
    void bootstrap();
  },
  { immediate: true },
);

watch(
  () => props.connectionId,
  (id, prev) => {
    if (id === prev) return;
    if (!id) {
      items.value = [];
      return;
    }
    void nextTick(() => loadPreview());
  },
);
</script>

<style scoped>
.panel-push-empty {
  padding: 16px 0 8px;
}
</style>
