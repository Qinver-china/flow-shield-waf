<template>
  <div class="filter-editor">
    <div
      v-for="condition in filterState.draftConditions.value"
      :key="condition.id"
      class="filter-editor-row"
    >
      <log-filter-field-picker
        v-model="condition.field"
        class="field-select"
        :get-popup-container="popupContainer"
        @change="onFieldChange(condition)"
      />
      <a-select
        v-model:value="condition.operator"
        class="operator-select"
        :get-popup-container="popupContainer"
        :options="operatorOptions(condition.field)"
      />
      <div class="value-input">
        <template v-if="currentField(condition)?.type === 'cookie'">
          <a-input
            :value="condition.arg || ''"
            allow-clear
            class="cookie-arg-input"
            :placeholder="currentField(condition)?.argPlaceholder || 'Cookie 参数名'"
            @update:value="setArgValue(condition, $event)"
          />
          <a-input
            :value="stringValue(condition)"
            allow-clear
            :placeholder="currentField(condition)?.placeholder || '参数值'"
            @update:value="setStringValue(condition, $event)"
          />
        </template>
        <site-single-select
          v-else-if="currentField(condition)?.type === 'site'"
          :value="siteValue(condition)"
          :get-popup-container="popupContainer"
          @update:value="setSiteValue(condition, $event)"
        />
        <a-input-number
          v-else-if="currentField(condition)?.type === 'rule_id'"
          :value="numberValue(condition)"
          :min="1"
          style="width: 100%"
          placeholder="输入规则 ID"
          @update:value="setNumberValue(condition, $event)"
        />
        <a-input-number
          v-else-if="currentField(condition)?.type === 'number'"
          :value="numberValue(condition)"
          :min="0"
          style="width: 100%"
          :placeholder="currentField(condition)?.placeholder || '输入数值'"
          @update:value="setNumberValue(condition, $event)"
        />
        <a-select
          v-else-if="currentField(condition)?.type === 'bool'"
          :value="boolValue(condition)"
          allow-clear
          style="width: 100%"
          placeholder="选择"
          :get-popup-container="popupContainer"
          :options="boolOptions(condition)"
          @update:value="setBoolValue(condition, $event)"
        />
        <a-select
          v-else-if="currentField(condition)?.type === 'select' && supportsMulti(condition)"
          :value="arrayValue(condition)"
          mode="tags"
          allow-clear
          show-search
          option-filter-prop="label"
          style="width: 100%"
          placeholder="选择或输入"
          :get-popup-container="popupContainer"
          :options="currentField(condition)?.options || []"
          @update:value="setArrayValue(condition, $event)"
        />
        <a-auto-complete
          v-else-if="currentField(condition) && isSuggestFilterField(currentField(condition)!)"
          :value="stringValue(condition)"
          allow-clear
          style="width: 100%"
          :placeholder="currentField(condition)?.placeholder || '选择或输入'"
          :get-popup-container="popupContainer"
          :options="(currentField(condition)?.options || []).map((o) => ({ value: o.value, label: o.label }))"
          option-filter-prop="label"
          @update:value="setStringValue(condition, $event)"
        />
        <a-select
          v-else-if="currentField(condition)?.type === 'select'"
          :value="stringValue(condition)"
          allow-clear
          show-search
          option-filter-prop="label"
          style="width: 100%"
          placeholder="选择"
          :get-popup-container="popupContainer"
          :options="currentField(condition)?.options || []"
          @update:value="setStringValue(condition, $event)"
        />
        <a-input
          v-else
          :value="stringValue(condition)"
          allow-clear
          :placeholder="currentField(condition)?.placeholder || '输入筛选值'"
          @update:value="setStringValue(condition, $event)"
        />
      </div>
      <a-button
        type="text"
        danger
        class="remove-btn"
        @click="filterState.removeDraftCondition(condition.id)"
      >
        <delete-outlined />
      </a-button>
    </div>

    <a-button type="link" class="add-and-btn" @click="filterState.addDraftCondition()">
      + 添加 And 条件
    </a-button>

    <div class="filter-editor-actions">
      <a-button @click="emit('cancel')" size="large">取消</a-button>
      <a-button type="primary" @click="emit('apply')" size="large">应用</a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { DeleteOutlined } from "@ant-design/icons-vue";
import SiteSingleSelect from "@/components/SiteSingleSelect.vue";
import LogFilterFieldPicker from "./LogFilterFieldPicker.vue";
import {
  defaultOperatorForField,
  findLogFilterField,
  getOperatorsForField,
  isSuggestFilterField,
  supportsMultiValue,
  type LogFilterCondition,
  type LogFilterOperator,
} from "./constants";
import type { LogFilterState } from "./useLogFilterState";

defineProps<{
  filterState: LogFilterState;
  popupContainer?: (triggerNode: HTMLElement) => HTMLElement;
}>();

const emit = defineEmits<{
  apply: [];
  cancel: [];
}>();

function currentField(condition: LogFilterCondition) {
  return findLogFilterField(condition.field);
}

function operatorOptions(fieldKey: string) {
  const field = findLogFilterField(fieldKey);
  if (!field) return [];
  return getOperatorsForField(field).map((value) => ({
    value,
    label: operatorLabel(value),
  }));
}

function operatorLabel(value: LogFilterOperator) {
  const map: Record<LogFilterOperator, string> = {
    eq: "等于",
    contains: "包含",
    ne: "不等于",
    not_contains: "不包含",
    like: "模糊匹配",
  };
  return map[value];
}

function onFieldChange(condition: LogFilterCondition) {
  const field = currentField(condition);
  if (!field) return;
  condition.operator = defaultOperatorForField(field);
  condition.value = supportsMultiValue(field) ? [] : "";
  condition.arg = field.type === "cookie" ? "" : undefined;
}

function supportsMulti(condition: LogFilterCondition) {
  const field = currentField(condition);
  return !!field && supportsMultiValue(field);
}

function stringValue(condition: LogFilterCondition) {
  return typeof condition.value === "string" ? condition.value : "";
}

function setStringValue(condition: LogFilterCondition, value?: string) {
  condition.value = value ?? "";
}

function setArgValue(condition: LogFilterCondition, value?: string) {
  condition.arg = value ?? "";
}

function arrayValue(condition: LogFilterCondition) {
  return Array.isArray(condition.value) ? condition.value : [];
}

function setArrayValue(condition: LogFilterCondition, value?: string[]) {
  condition.value = value ?? [];
}

function numberValue(condition: LogFilterCondition) {
  const raw = Array.isArray(condition.value) ? condition.value[0] : condition.value;
  if (!raw) return undefined;
  const num = Number(raw);
  return Number.isFinite(num) ? num : undefined;
}

function setNumberValue(condition: LogFilterCondition, value?: number | null) {
  condition.value = value == null ? "" : String(value);
}

function siteValue(condition: LogFilterCondition) {
  const num = numberValue(condition);
  return num ?? undefined;
}

function setSiteValue(condition: LogFilterCondition, value?: number) {
  condition.value = value == null ? "" : String(value);
}

function boolValue(condition: LogFilterCondition) {
  return stringValue(condition) || undefined;
}

function setBoolValue(condition: LogFilterCondition, value?: string) {
  condition.value = value ?? "";
}

function boolOptions(condition: LogFilterCondition) {
  if (condition.field === "blocked") {
    return [
      { value: "true", label: "已拦截" },
      { value: "false", label: "已放行" },
    ];
  }
  return [
    { value: "true", label: "是" },
    { value: "false", label: "否" },
  ];
}
</script>

<style scoped>
.value-input {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cookie-arg-input {
  width: 100%;
}

.filter-editor {
  width: 100%;
}

.filter-editor-row {
  display: grid;
  grid-template-columns: minmax(140px, 1.2fr) 108px minmax(180px, 1.6fr) 32px;
  gap: 8px;
  align-items: center;
}

.filter-editor-row + .filter-editor-row {
  margin-top: 8px;
}

.add-and-btn {
  margin-top: 4px;
  padding-inline: 0;
}
.ant-drawer-body .add-and-btn{
  width: 100%;
}

.filter-editor-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
}
.filter-editor-actions >*{
  flex: 1;
}

@media (max-width: 1023px) {
  .filter-editor-row + .filter-editor-row {
    margin-top: 0;
  }

  .filter-editor-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 104px;
    grid-template-areas:
      "field operator"
      "value remove";
    gap: 8px;
    align-items: center;
    padding-bottom: 12px;
    margin-bottom: 12px;
    border-bottom: 1px solid var(--fs-border);
  }

  .filter-editor-row:last-of-type {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
  }

  .field-select {
    grid-area: field;
    min-width: 0;
  }

  .operator-select {
    grid-area: operator;
    width: 100%;
    min-width: 0;
  }

  .value-input {
    grid-area: value;
    min-width: 0;
  }

  .remove-btn {
    grid-area: remove;
    justify-self: end;
    align-self: center;
  }
}
</style>
