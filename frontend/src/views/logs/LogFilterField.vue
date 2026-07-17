<template>
  <a-form-item :label="field.label">
    <site-single-select
      v-if="field.type === 'site'"
      v-model:value="filters.site_id"
    />
    <a-input-number
      v-else-if="field.type === 'rule_id'"
      v-model:value="filters.rule_id"
      :min="1"
      style="width: 100%"
      placeholder="全部"
    />
    <a-input-number
      v-else-if="field.type === 'number'"
      v-model:value="filters.geo_asn"
      :min="1"
      style="width: 100%"
      :placeholder="field.placeholder || '全部'"
    />
    <a-select
      v-else-if="field.type === 'bool' && field.key === 'blocked'"
      v-model:value="filters.blocked"
      allow-clear
      placeholder="全部"
    >
      <a-select-option :value="true">已拦截</a-select-option>
      <a-select-option :value="false">已放行</a-select-option>
    </a-select>
    <a-select
      v-else-if="field.type === 'bool'"
      :value="getBoolFilter(field.key)"
      allow-clear
      placeholder="全部"
      :options="boolFilterOptions"
      @update:value="setBoolFilter(field.key, $event)"
    />
    <a-select
      v-else-if="field.type === 'select'"
      :value="getSelectFilter(field.key)"
      allow-clear
      placeholder="全部"
      :options="field.options"
      @update:value="setSelectFilter(field.key, $event)"
    />
    <a-input
      v-else
      :value="getTextFilter(field.key)"
      allow-clear
      :placeholder="field.placeholder || field.label"
      @update:value="setTextFilter(field.key, $event)"
    />
  </a-form-item>
</template>

<script setup lang="ts">
import SiteSingleSelect from "@/components/SiteSingleSelect.vue";
import { boolFilterOptions, type LogDetailFilters, type LogFilterFieldDef } from "./constants";
import { useLogFilterFieldBindings } from "./useLogFilterField";

const props = defineProps<{
  field: LogFilterFieldDef;
  filters: LogDetailFilters;
}>();

const { getTextFilter, setTextFilter, getSelectFilter, setSelectFilter, getBoolFilter, setBoolFilter } =
  useLogFilterFieldBindings(props.filters);
</script>
