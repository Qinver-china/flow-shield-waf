<template>
  <a-select
    v-if="!readonly"
    v-model:value="model"
    allow-clear
    placeholder="不选表示全站"
    :options="selectOptions"
    :loading="loading"
    :disabled="disabled"
    show-search
    option-filter-prop="label"
    style="width: 100%"
  />
  <span v-else>{{ formatSiteId(value) }}</span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useSiteOptions } from "@/composables/useSiteOptions";

const props = withDefaults(
  defineProps<{
    value?: number | null;
    readonly?: boolean;
    disabled?: boolean;
  }>(),
  {
    value: undefined,
    readonly: false,
    disabled: false,
  },
);

const emit = defineEmits<{ "update:value": [number | undefined] }>();

const { selectOptions, loading, formatSiteId } = useSiteOptions();

const model = computed({
  get: () => props.value ?? undefined,
  set: (id: number | undefined) => emit("update:value", id),
});
</script>
