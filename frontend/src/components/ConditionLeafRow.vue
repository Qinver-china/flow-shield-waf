<template>
  <div v-if="readonly" class="cond-leaf-readonly">
    {{ formatLeafRow(row, fieldMap, operators, ipGroupLabel) }}
  </div>
  <div v-else-if="isWindowCompareField(row.field)" class="cond-row cond-traffic-row">
    <condition-field-picker
      v-model:value="row.field"
      :catalog="catalog"
      :field-map="fieldMap"
      @change="() => onFieldChange(row, fieldMap)"
    />

    <a-select
      v-model:value="row.trafficWindow"
      class="traffic-window-select"
      placeholder="时间窗口"
    >
      <a-select-option
        v-for="opt in optionsFor(fieldMap, row.field)"
        :key="opt.value"
        :value="Number(opt.value)"
      >
        {{ opt.label }}
      </a-select-option>
    </a-select>

    <a-select
      v-model:value="row.trafficCompare"
      class="traffic-compare-select"
      placeholder="判断方式"
    >
      <a-select-option
        v-for="opt in compareModesFor(fieldMap, row.field)"
        :key="opt.value"
        :value="opt.value"
      >
        {{ opt.label }}
      </a-select-option>
    </a-select>

    <a-input-number
      v-if="isTrafficBaselineCompare(row.trafficCompare)"
      v-model:value="row.trafficPercent"
      class="value-input"
      :min="0"
      :precision="0"
      addon-after="%"
      placeholder="百分比"
    />

    <a-input-number
      v-else
      v-model:value="row.trafficThreshold"
      class="value-input"
      :min="0"
      :precision="thresholdPrecision"
      :addon-after="thresholdAddon"
      :placeholder="thresholdPlaceholder"
    />

    <a-button danger size="small" type="text" @click="$emit('remove')">删除</a-button>
  </div>
  <div v-else class="cond-row">
    <condition-field-picker
      v-model:value="row.field"
      :catalog="catalog"
      :field-map="fieldMap"
      @change="() => onFieldChange(row, fieldMap)"
    />

    <a-input
      v-if="fieldMap[row.field || '']?.requires_arg"
      v-model:value="row.arg"
      class="arg-input"
      placeholder="子键"
    />

    <a-select
      v-model:value="row.op"
      class="op-select"
      placeholder="操作符"
      @change="() => onOpChange(row, fieldMap)"
    >
      <a-select-option v-for="op in opsFor(fieldMap, row.field)" :key="op" :value="op">
        {{ operators[op] || op }}
      </a-select-option>
    </a-select>

    <a-select
      v-if="hasOptions(fieldMap, row.field) && isListOp(row.op)"
      v-model:value="row.valueList"
      mode="tags"
      class="value-input"
      placeholder="选择或输入（可搜索，回车添加）"
      show-search
      option-filter-prop="label"
      :options="optionsFor(fieldMap, row.field)"
    />

    <a-auto-complete
      v-else-if="hasOptions(fieldMap, row.field) && !isBoolField(fieldMap, row.field)"
      v-model:value="row.valueText"
      class="value-input"
      placeholder="选择或输入（可搜索）"
      :options="autoCompleteOptions(fieldMap, row.field)"
      option-filter-prop="label"
    />

    <a-select
      v-else-if="hasOptions(fieldMap, row.field)"
      v-model:value="row.valueText"
      class="value-input"
      placeholder="请选择"
      show-search
      option-filter-prop="label"
      :options="optionsFor(fieldMap, row.field)"
    />

    <a-select
      v-else-if="isIpGroupOp(row.op)"
      v-model:value="row.valueList"
      mode="multiple"
      class="value-input"
      placeholder="选择 IP 组"
      option-filter-prop="label"
      :options="ipGroupSelectOptions"
      :loading="!ipGroupOptions?.length"
    />

    <a-select
      v-else-if="(isListOp(row.op) && !hasOptions(fieldMap, row.field)) || isStringMultiOp(row.op)"
      v-model:value="row.valueList"
      mode="tags"
      class="value-input"
      placeholder="回车添加"
      :open="false"
      :token-separators="[]"
    />

    <a-input-number
      v-else-if="isNumberOp(row.op)"
      v-model:value="row.valueNumber"
      class="value-input"
      :min="0"
      :precision="0"
      placeholder="长度"
    />

    <a-input
      v-else-if="row.op && !NO_VALUE_OPS.includes(row.op)"
      v-model:value="row.valueText"
      class="value-input"
      placeholder="值"
    />

    <a-button danger size="small" type="text" @click="$emit('remove')">删除</a-button>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import ConditionFieldPicker from "@/components/ConditionFieldPicker.vue";
import type { Category, Field, UiLeaf } from "@/composables/useConditionModel";
import type { IpGroupOption } from "@/composables/useIpGroupOptions";
import {
  NO_VALUE_OPS,
  autoCompleteOptions,
  compareModesFor,
  formatLeafRow,
  hasOptions,
  isBoolField,
  isIpGroupOp,
  isListOp,
  isNumberOp,
  isStringMultiOp,
  isSystemCpuPctCompare,
  isTrafficBaselineCompare,
  isTrafficQpsCompare,
  isWindowCompareField,
  onFieldChange,
  onOpChange,
  opsFor,
  optionsFor,
} from "@/composables/useConditionModel";

const props = defineProps<{
  row: UiLeaf;
  catalog: Category[];
  fieldMap: Record<string, Field>;
  operators: Record<string, string>;
  ipGroupOptions?: IpGroupOption[];
  ipGroupLabel?: (id: string) => string;
  readonly?: boolean;
}>();

defineEmits<{ remove: [] }>();

const thresholdPrecision = computed(() => {
  if (isTrafficQpsCompare(props.row.trafficCompare)) return 2;
  if (isSystemCpuPctCompare(props.row.trafficCompare)) return 1;
  return 0;
});

const thresholdAddon = computed(() => {
  if (isTrafficQpsCompare(props.row.trafficCompare)) return "QPS";
  if (isSystemCpuPctCompare(props.row.trafficCompare)) return "%";
  return undefined;
});

const thresholdPlaceholder = computed(() => {
  if (isTrafficQpsCompare(props.row.trafficCompare)) return "QPS";
  if (isSystemCpuPctCompare(props.row.trafficCompare)) return "CPU%";
  return "请求量";
});

const ipGroupSelectOptions = computed(() =>
  (props.ipGroupOptions || []).map((item) => ({
    value: String(item.id),
    label: `${item.name}（${item.entry_count}）`,
  })),
);
</script>

<style scoped>
.cond-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.cond-traffic-row .traffic-window-select {
  width: 128px;
  min-width: 128px;
}
.cond-traffic-row .traffic-compare-select {
  width: 148px;
}
.arg-input {
  width: 96px;
}
.op-select {
  width: 108px;
}
.value-input {
  flex: 1;
  min-width: 110px;
}
.cond-leaf-readonly {
  padding: 4px 0 4px 12px;
  color: #334155;
  line-height: 1.5;
}
</style>
