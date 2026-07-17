<template>
  <a-drawer
    :open="open"
    :width="resolvedWidth"
    :destroy-on-close="destroyOnClose"
    placement="right"
    class="fs-detail-drawer"
    @update:open="emit('update:open', $event)"
  >
    <template #title>
      <div class="fs-drawer-headline">
        <span class="fs-drawer-title-text">{{ title }}</span>
        <span v-if="subtitle" class="fs-drawer-title-meta">· {{ subtitle }}</span>
      </div>
    </template>

    <a-spin :spinning="loading">
      <div class="fs-detail-surface">
        <slot />
        <fs-json-block v-if="jsonContent" :content="jsonContent" :title="jsonTitle" />
      </div>
    </a-spin>

    <template v-if="$slots.footer" #footer>
      <div class="fs-detail-actions">
        <slot name="footer" />
      </div>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed } from "vue";
import FsJsonBlock from "@/components/FsJsonBlock.vue";
import { useBreakpoint } from "@/composables/useBreakpoint";

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    subtitle?: string;
    width?: number;
    loading?: boolean;
    jsonContent?: string;
    jsonTitle?: string;
    destroyOnClose?: boolean;
  }>(),
  {
    width: 760,
    loading: false,
    jsonTitle: "JSON 数据",
    destroyOnClose: true,
  },
);

const emit = defineEmits<{
  "update:open": [boolean];
}>();

const { isMobile } = useBreakpoint();
const resolvedWidth = computed(() => (isMobile.value ? "100%" : props.width));
</script>
