<template>
  <fs-detail-drawer
    :open="open"
    :loading="loading"
    title="日志详情"
    :subtitle="detail?.request_id || undefined"
    :width="800"
    @update:open="emit('update:open', $event)"
  >
    <template v-if="detail">
      <fs-detail-section title="概要">
        <fs-detail-kv :items="summaryItems" />
      </fs-detail-section>

      <fs-detail-section title="请求快照">
        <fs-detail-kv :items="requestItems" />
      </fs-detail-section>

      <fs-detail-section v-if="headerRows.length" :title="`请求头（${headerRows.length}）`">
        <fs-detail-kv :items="headerKvItems" />
      </fs-detail-section>

      <fs-detail-section
        v-if="cookieRows.length || detail.payload?.cookie_raw"
        :title="`Cookie（${cookieRows.length || 1}）`"
      >
        <fs-detail-kv :items="cookieKvItems" />
      </fs-detail-section>

      <fs-detail-section v-if="queryRows.length" :title="`查询参数（${queryRows.length}）`">
        <a-table
          :columns="kvColumns"
          :data-source="queryRows"
          :pagination="false"
          size="middle"
          row-key="key"
        />
      </fs-detail-section>

      <fs-detail-section v-if="evaluatedRows.length" :title="`规则判定扩展字段（${evaluatedRows.length}）`">
        <a-table
          :columns="evaluatedColumns"
          :data-source="evaluatedRows"
          :pagination="false"
          size="middle"
          row-key="key"
        />
      </fs-detail-section>

      <a-empty
        v-if="!headerRows.length && !cookieRows.length && !queryRows.length && !evaluatedRows.length"
        description="暂无请求快照（旧日志或未命中采样）"
        style="margin-top: 8px"
      />
    </template>
  </fs-detail-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { api } from "@/api";
import FsDetailDrawer from "@/components/FsDetailDrawer.vue";
import FsDetailKv from "@/components/FsDetailKv.vue";
import FsDetailSection from "@/components/FsDetailSection.vue";
import { useSiteOptions } from "@/composables/useSiteOptions";
import { modeColor, modeLabel, sourceLabel } from "./constants";
import { formatTs } from "./useLogTimeRange";

const { formatSiteId } = useSiteOptions();

const props = defineProps<{ open: boolean; logId?: string | null }>();
const emit = defineEmits<{ "update:open": [boolean] }>();

const loading = ref(false);
const detail = ref<any>(null);
const fieldMeta = ref<Record<string, { label: string; category: string }>>({});

const evaluatedColumns = [
  { title: "分类", dataIndex: "category", width: 120 },
  { title: "字段", dataIndex: "label", width: 180 },
  { title: "参数", dataIndex: "arg", width: 120 },
  { title: "取值", dataIndex: "value", ellipsis: true },
];

const kvColumns = [
  { title: "名称", dataIndex: "name", width: 220, ellipsis: true },
  { title: "取值", dataIndex: "value", ellipsis: true },
];

function mapToRows(map: Record<string, unknown> | undefined | null) {
  if (!map || typeof map !== "object") return [];
  return Object.keys(map)
    .sort((a, b) => a.localeCompare(b))
    .map((name) => ({
      key: name,
      name,
      value: map[name] == null || map[name] === "" ? "-" : String(map[name]),
    }));
}

const headerRows = computed(() => mapToRows(detail.value?.payload?.headers));
const cookieRows = computed(() => mapToRows(detail.value?.payload?.cookies));
const queryRows = computed(() => mapToRows(detail.value?.payload?.query));

const summaryItems = computed(() => {
  const d = detail.value;
  if (!d) return [];
  return [
    { label: "时间", value: formatTs(d.ts) },
    { label: "类型", value: sourceLabel[d.source] || d.source || "-" },
    { label: "模式", value: modeLabel[d.mode] || d.mode || "-", tag: true, tagColor: modeColor[d.mode] || "default" },
    { label: "请求域名", value: d.domain || "-" },
    { label: "客户端 IP", value: d.client_ip || "-" },
    { label: "地理位置", value: d.geo_country || "（未查询）" },
    { label: "请求方法", value: d.method || "-" },
    { label: "原始请求行", value: d.request_uri || d.uri || "-" },
    { label: "请求路径", value: d.uri_path || "-" },
    { label: "文件后缀", value: d.uri_ext || "-" },
    { label: "路径深度", value: d.uri_depth ?? "-" },
    { label: "原始查询串", value: d.uri_query || "-" },
    { label: "Referer", value: d.referer || "-" },
    { label: "User-Agent", value: d.ua || "-" },
    {
      label: "命中规则",
      value: d.rule_name ? `${d.rule_name} (#${d.rule_id})` : "-",
    },
    { label: "请求 ID", value: d.request_id || "-" },
    { label: "站点", value: formatSiteId(d.site_id) },
    { label: "是否拦截", value: d.blocked ? "是" : "否" },
  ];
});

const requestItems = computed(() => {
  const d = detail.value;
  if (!d) return [];
  return [
    { label: "客户端 IP", value: d.payload?.client?.ip || d.client_ip || "-" },
    { label: "客户端端口", value: d.payload?.client?.port ?? "-" },
    { label: "协议", value: d.payload?.request?.scheme || "-" },
    { label: "完整 URL", value: d.payload?.request?.url || "-" },
    { label: "HTTP 版本", value: d.payload?.request?.http_version || "-" },
  ];
});

const headerKvItems = computed(() =>
  headerRows.value.map((row) => ({ label: row.name, value: row.value })),
);

const cookieKvItems = computed(() => {
  const items = cookieRows.value.map((row) => ({ label: row.name, value: row.value }));
  if (detail.value?.payload?.cookie_raw) {
    items.push({ label: "原始 Cookie", value: detail.value.payload.cookie_raw });
  }
  return items;
});

function fieldLabel(field: string, arg?: string | null) {
  const meta = fieldMeta.value[field];
  const base = meta?.label || field;
  if (
    field === "http.header" ||
    field === "http.query" ||
    field === "http.cookie" ||
    field === "http.body.form" ||
    field === "http.body.json" ||
    field === "http.uri.segment"
  ) {
    return arg ? `${base} (${arg})` : base;
  }
  return base;
}

const evaluatedRows = computed(() => {
  const list = detail.value?.payload?.evaluated;
  if (!Array.isArray(list)) return [];
  return list.map((item: any, idx: number) => {
    const field = item.field || "";
    const meta = fieldMeta.value[field];
    return {
      key: `${field}|${item.arg || ""}|${idx}`,
      category: meta?.category || "-",
      label: fieldLabel(field, item.arg),
      arg: item.arg || "-",
      value: item.value == null || item.value === "" ? "-" : String(item.value),
    };
  });
});

async function loadFieldMeta() {
  if (Object.keys(fieldMeta.value).length) return;
  const resp = await api.get<{ categories: { name: string; fields: { key: string; label: string }[] }[] }>(
    "/api/v1/meta/fields",
  );
  const map: Record<string, { label: string; category: string }> = {};
  for (const cat of resp.data.categories || []) {
    for (const f of cat.fields || []) {
      map[f.key] = { label: f.label, category: cat.name };
    }
  }
  fieldMeta.value = map;
}

async function loadDetail(id: string) {
  loading.value = true;
  detail.value = null;
  try {
    await loadFieldMeta();
    const resp = await api.get(`/api/v1/logs/${id}`);
    detail.value = resp.data;
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.open, props.logId] as const,
  ([isOpen, id]) => {
    if (isOpen && id) loadDetail(id);
  },
  { immediate: true },
);
</script>
