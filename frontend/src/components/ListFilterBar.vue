<template>
  <div v-if="fields.length || $slots.extra" class="filter-bar">
    <a-space wrap :size="12" align="start" class="filter-bar-controls">
      <template v-for="field in fields" :key="field.key">
        <a-input-search
          v-if="field.type === 'search'"
          v-model:value="model[field.key]"
          :placeholder="field.placeholder || field.label"
          allow-clear
          class="filter-control filter-control--search"
          :style="controlStyle(field, 'search')"
          @search="emit('change')"
        />
        <a-select
          v-else-if="field.type === 'select'"
          v-model:value="model[field.key]"
          :options="field.options"
          :placeholder="field.placeholder || field.label"
          :mode="field.multiple ? 'multiple' : undefined"
          :max-tag-count="field.multiple ? 'responsive' : undefined"
          allow-clear
          show-search
          option-filter-prop="label"
          class="filter-control filter-control--select"
          :class="{ 'filter-control--select-multi': field.multiple }"
          :style="controlStyle(field, field.multiple ? 'select-multi' : 'select')"
          @change="emit('change')"
        />
        <a-select
          v-else-if="field.type === 'site'"
          v-model:value="model[field.key]"
          :options="siteSelectOptions"
          :loading="sitesLoading"
          :placeholder="field.placeholder || field.label || '生效站点'"
          :mode="field.multiple ? 'multiple' : undefined"
          :max-tag-count="field.multiple ? 'responsive' : undefined"
          allow-clear
          show-search
          option-filter-prop="label"
          class="filter-control filter-control--site"
          :class="{ 'filter-control--site-multi': field.multiple }"
          :style="controlStyle(field, field.multiple ? 'site-multi' : 'site')"
          @change="emit('change')"
        />
      </template>
      <a-button v-if="fields.length" @click="emit('reset')">重置</a-button>
    </a-space>
    <div v-if="$slots.extra" class="filter-bar-extra">
      <slot name="extra" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSiteOptions } from "@/composables/useSiteOptions";
import type { ResourceFilterField } from "@/types/resourceList";

defineProps<{
  fields: ResourceFilterField[];
  model: Record<string, unknown>;
}>();

const emit = defineEmits<{
  change: [];
  reset: [];
}>();

const { selectOptions: siteSelectOptions, loading: sitesLoading } = useSiteOptions();

const defaultWidths: Record<string, string> = {
  search: "260px",
  select: "200px",
  "select-multi": "280px",
  site: "240px",
  "site-multi": "320px",
};

function controlStyle(field: ResourceFilterField, type: string) {
  const width = field.width ? String(field.width) : defaultWidths[type] ?? defaultWidths.site;
  return { width, minWidth: width };
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 24px;
}

.filter-bar-controls {
  flex: 1;
  min-width: 0;
}

.filter-bar-extra {
  flex-shrink: 0;
}

.filter-bar-head {
  margin-bottom: 12px;
}

.filter-bar-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--fs-text-secondary);
  letter-spacing: 0.02em;
}

.filter-bar :deep(.filter-control) {
  flex-shrink: 0;
}

.filter-bar :deep(.filter-control .ant-select-selector) {
  min-height: 32px;
}

.filter-bar :deep(.filter-control .ant-select-selection-item),
.filter-bar :deep(.filter-control .ant-select-selection-placeholder) {
  line-height: 30px;
}

@media (max-width: 767px) {
  .filter-bar :deep(.ant-space) {
    width: 100%;
  }

  .filter-bar :deep(.ant-space-item) {
    width: 100%;
  }

  .filter-bar :deep(.filter-control) {
    width: 100% !important;
    min-width: 0 !important;
  }
}
</style>
