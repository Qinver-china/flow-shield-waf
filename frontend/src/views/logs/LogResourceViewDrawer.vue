<template>
  <fs-form-drawer
    :open="open"
    mode="view"
    :title="title"
    :subtitle="subtitle"
    :loading="loading"
    :json-content="jsonContent"
    json-title="配置详情"
    @update:open="emit('update:open', $event)"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { message } from "ant-design-vue";
import { api } from "@/api";
import FsFormDrawer from "@/components/FsFormDrawer.vue";
import type { LogResourceViewTarget } from "./constants";

const props = defineProps<{
  open: boolean;
  target: LogResourceViewTarget | null;
}>();

const emit = defineEmits<{ "update:open": [boolean] }>();

const loading = ref(false);
const record = ref<Record<string, unknown> | null>(null);

const title = computed(() => {
  if (!props.target) return "查看详情";
  if (props.target.kind === "route") return props.target.title;
  return props.target.title;
});

const subtitle = computed(() => {
  if (!props.target || props.target.kind === "route") return undefined;
  if (props.target.kind === "bot_by_name") return props.target.name;
  return `#${props.target.id}`;
});

const jsonContent = computed(() =>
  record.value ? JSON.stringify(record.value, null, 2) : "",
);

async function fetchRecord() {
  const target = props.target;
  if (!target || target.kind === "route") {
    record.value = null;
    return;
  }

  loading.value = true;
  record.value = null;
  try {
    if (target.kind === "api") {
      const resp = await api.get(`${target.apiBase}/${target.id}`);
      record.value = resp.data;
      return;
    }

    const resp = await api.get("/api/v1/bots", {
      page: 1,
      page_size: 20,
      q: target.name,
    });
    const items = resp.data?.items || [];
    const exact = items.find((item: { name?: string }) => item.name === target.name);
    record.value = exact || items[0] || null;
    if (!record.value) {
      message.warning("未找到对应 Bot 配置");
    }
  } catch {
    message.error("加载配置失败");
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.open, props.target] as const,
  ([open, target]) => {
    if (!open || !target || target.kind === "route") return;
    void fetchRecord();
  },
);
</script>
