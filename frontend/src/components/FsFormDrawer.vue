<template>
  <a-drawer
    :open="open"
    :width="resolvedWidth"
    :destroy-on-close="destroyOnClose"
    :z-index="zIndex"
    placement="right"
    class="fs-form-drawer"
    @update:open="emit('update:open', $event)"
  >
    <template #title>
      <div class="fs-drawer-headline">
        <span class="fs-drawer-badge" :class="badgeClass">{{ modeLabel }}</span>
        <span class="fs-drawer-title-text">{{ title }}</span>
        <span v-if="subtitle" class="fs-drawer-title-meta">· {{ subtitle }}</span>
      </div>
    </template>

    <a-spin :spinning="loading">
      <div :class="surfaceClass">
        <slot />
        <fs-json-block
          v-if="mode === 'view' && jsonContent"
          :content="jsonContent"
          :title="jsonTitle"
        />
      </div>
    </a-spin>

    <template v-if="mode === 'view' ? $slots['view-actions'] : true" #footer>
      <div class="fs-detail-actions">
        <slot v-if="mode === 'view'" name="view-actions" />
        <template v-else>
          <a-button @click="onCancel">{{ cancelText }}</a-button>
          <a-button type="primary" :loading="confirmLoading" @click="emit('ok')">{{ okText }}</a-button>
        </template>
      </div>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed } from "vue";
import FsJsonBlock from "@/components/FsJsonBlock.vue";
import { useBreakpoint } from "@/composables/useBreakpoint";

export type FormDrawerMode = "create" | "edit" | "copy" | "view";

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    subtitle?: string;
    mode?: FormDrawerMode;
    width?: number;
    loading?: boolean;
    confirmLoading?: boolean;
    okText?: string;
    cancelText?: string;
    jsonContent?: string;
    jsonTitle?: string;
    destroyOnClose?: boolean;
    zIndex?: number;
  }>(),
  {
    mode: "create",
    width: 760,
    loading: false,
    okText: "保存",
    cancelText: "取消",
    destroyOnClose: true,
    jsonTitle: "JSON 数据",
  },
);

const emit = defineEmits<{
  "update:open": [boolean];
  ok: [];
  cancel: [];
}>();

const { isMobile } = useBreakpoint();

const modeLabel = computed(() => {
  if (props.mode === "view") return "查看";
  if (props.mode === "edit") return "编辑";
  if (props.mode === "copy") return "复制";
  return "新增";
});

const badgeClass = computed(() => {
  if (props.mode === "view") return "is-view";
  if (props.mode === "edit") return "is-edit";
  if (props.mode === "copy") return "is-copy";
  return "is-create";
});

const surfaceClass = computed(() =>
  props.mode === "view" ? "fs-detail-surface" : "fs-form-surface",
);

const resolvedWidth = computed(() => (isMobile.value ? "100%" : props.width));

function onCancel() {
  emit("cancel");
  emit("update:open", false);
}
</script>
