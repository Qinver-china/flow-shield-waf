<template>
  <div v-if="fields.length" class="" style="margin-bottom: 24px;">
    <a-space wrap :size="12" align="start">
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
          allow-clear
          class="filter-control filter-control--select"
          :style="controlStyle(field, 'select')"
          @change="emit('change')"
        />
        <a-select
          v-else-if="field.type === 'site'"
          v-model:value="model[field.key]"
          :options="siteSelectOptions"
          :loading="sitesLoading"
          :placeholder="field.placeholder || '生效站点'"
          allow-clear
          show-search
          option-filter-prop="label"
          class="filter-control filter-control--site"
          :style="controlStyle(field, 'site')"
          @change="emit('change')"
        />
      </template>
      <a-button @click="emit('reset')">重置</a-button>
    </a-space>
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

const defaultWidths: Record<ResourceFilterField["type"], string> = {
  search: "260px",
  select: "200px",
  site: "240px",
};

function controlStyle(field: ResourceFilterField, type: ResourceFilterField["type"]) {
  const width = field.width ? String(field.width) : defaultWidths[type];
  return { width, minWidth: width };
}
</script>

<style scoped>
.filter-bar {
  padding: 14px 16px;
  margin-bottom: var(--fs-space-md);
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
