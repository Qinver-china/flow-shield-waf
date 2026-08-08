<template>
  <a-select
    v-model:value="selected"
    allow-clear
    placeholder="全部站点合计"
    :options="options"
    :loading="loading"
    show-search
    option-filter-prop="label"
    style="width: 100%"
  />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useSiteOptions } from "@/composables/useSiteOptions";

const SCOPE_ALL = "all";
const SCOPE_ANY = "any";

const props = withDefaults(
  defineProps<{
    siteScope?: string | null;
    siteId?: number | null;
  }>(),
  {
    siteScope: undefined,
    siteId: undefined,
  },
);

const emit = defineEmits<{
  "update:siteScope": [string | undefined];
  "update:siteId": [number | undefined];
}>();

const { selectOptions, loading } = useSiteOptions();

const options = computed(() => [
  { value: SCOPE_ALL, label: "全部站点合计" },
  { value: SCOPE_ANY, label: "任意站点" },
  ...selectOptions.value,
]);

const selected = computed({
  get() {
    const scope = props.siteScope || (props.siteId != null ? "single" : SCOPE_ALL);
    if (scope === SCOPE_ANY) return SCOPE_ANY;
    if (scope === SCOPE_ALL || props.siteId == null) return SCOPE_ALL;
    return props.siteId;
  },
  set(value: string | number | undefined) {
    if (value == null || value === "") {
      emit("update:siteScope", SCOPE_ALL);
      emit("update:siteId", undefined);
      return;
    }
    if (value === SCOPE_ALL) {
      emit("update:siteScope", SCOPE_ALL);
      emit("update:siteId", undefined);
      return;
    }
    if (value === SCOPE_ANY) {
      emit("update:siteScope", SCOPE_ANY);
      emit("update:siteId", undefined);
      return;
    }
    emit("update:siteScope", "single");
    emit("update:siteId", Number(value));
  },
});
</script>
