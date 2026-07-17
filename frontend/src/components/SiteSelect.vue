<template>
  <a-select
    v-if="!readonly"
    v-model:value="model"
    mode="multiple"
    allow-clear
    placeholder="不选表示全局生效"
    :options="selectOptions"
    :loading="loading"
    :disabled="disabled"
    style="min-width: 280px"
  />
  <span v-else>{{ formatSiteIds(model) }}</span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useSiteOptions } from "@/composables/useSiteOptions";

const props = withDefaults(
  defineProps<{
    value?: number[];
    readonly?: boolean;
    disabled?: boolean;
  }>(),
  {
    value: () => [],
    readonly: false,
    disabled: false,
  },
);

const emit = defineEmits<{ "update:value": [number[]] }>();

const { selectOptions, loading, formatSiteIds } = useSiteOptions();

const model = computed({
  get: () => props.value ?? [],
  set: (ids: number[]) => emit("update:value", ids),
});
</script>
