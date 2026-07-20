<template>
  <div class="log-filter-bar">
    <a-card  class="time-bar">
      <div class="time-bar-inner">
        <div class="time-bar-presets">
          <a-select
            v-if="isCompact"
            :value="filterState.preset.value"
            
            class="preset-select"
            :options="presetOptions"
            @change="onPresetSelectChange"
          />
          <a-radio-group
            v-else
            :value="filterState.preset.value"
            button-style="solid"
            
            class="preset-group"
            @change="onPresetChange"
          >
            <a-radio-button
              v-for="item in quickTimePresets"
              :key="item.key"
              :value="item.key"
            >
              {{ item.label }}
            </a-radio-button>
            <a-radio-button value="custom">自定义</a-radio-button>
          </a-radio-group>
        </div>

        <div class="time-bar-meta">
          <a-range-picker
            v-if="filterState.preset.value === 'custom'"
            :value="filterState.customRange.value"
            show-time
            
            class="custom-range"
            @change="onCustomRangeChange"
          />
          <span v-else class="time-hint">{{ filterState.rangeLabel() }}</span>
          <a-button
            type="primary"
            class="refresh-btn"
            @click="props.filterState.bumpRefresh()"
          >
            刷新
          </a-button>
        </div>
      </div>
    </a-card>

    <a-card  class="filter-bar-card">
      <div class="filter-bar-inner">
        <filter-outlined class="filter-icon" />
        <div class="filter-content">
          <template v-if="filterState.hasAppliedFilters.value">
            <a-tag
              v-for="(label, index) in filterState.appliedFilterLabels.value"
              :key="`${label}-${index}`"
              closable
              class="filter-tag"
              @close.prevent="removeApplied(index)"
            >
              {{ label }}
            </a-tag>
          </template>
          <a-popover
            v-model:open="filterState.editorOpen.value"
            trigger="click"
            placement="bottomLeft"
            overlay-class-name="log-filter-editor-popover"
            @open-change="onEditorOpenChange"
          >
            <template #content>
              <div class="filter-editor">
                <div
                  v-for="condition in filterState.draftConditions.value"
                  :key="condition.id"
                  class="filter-editor-row"
                >
                  <log-filter-field-picker
                    v-model="condition.field"
                    class="field-select"
                    @change="onFieldChange(condition)"
                  />
                  <a-select
                    v-model:value="condition.operator"
                    
                    class="operator-select"
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
                      :options="currentField(condition)?.options || []"
                      @update:value="setArrayValue(condition, $event)"
                    />
                    <a-auto-complete
                      v-else-if="currentField(condition) && isSuggestFilterField(currentField(condition)!)"
                      :value="stringValue(condition)"
                      allow-clear
                      style="width: 100%"
                      :placeholder="currentField(condition)?.placeholder || '选择或输入'"
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
                    style="padding: 0;"
                    @click="filterState.removeDraftCondition(condition.id)"
                  >
                    <delete-outlined />
                  </a-button>
                </div>

                <a-button type="link"  class="add-and-btn" @click="filterState.addDraftCondition()">
                  + 添加 And 条件
                </a-button>

                <div class="filter-editor-actions">
                  <a-button type="primary"  @click="applyEditor">应用</a-button>
                  <a-button  @click="filterState.closeEditor()">取消</a-button>
                </div>
              </div>
            </template>
            <a-button type="link"  class="add-filter-btn" @click="openEditor">
              + 添加筛选
            </a-button>
          </a-popover>
          <a-button
            v-if="filterState.hasAppliedFilters.value"
            type="link"
            danger
            class="clear-filter-btn"
            @click="clearFilters"
          >
            清空筛选
          </a-button>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Dayjs } from "dayjs";
import { DeleteOutlined, FilterOutlined } from "@ant-design/icons-vue";
import SiteSingleSelect from "@/components/SiteSingleSelect.vue";
import { useBreakpoint } from "@/composables/useBreakpoint";
import LogFilterFieldPicker from "./LogFilterFieldPicker.vue";
import {
  defaultOperatorForField,
  findLogFilterField,
  getOperatorsForField,
  isSuggestFilterField,
  supportsMultiValue,
  timePresets,
  type LogFilterCondition,
  type LogFilterOperator,
  type TimePreset,
} from "./constants";
import type { LogFilterState } from "./useLogFilterState";

const props = defineProps<{
  filterState: LogFilterState;
}>();

const { isMobile, isTablet } = useBreakpoint();
const isCompact = computed(() => isMobile.value || isTablet.value);

const quickTimePresets = timePresets.filter((item) => item.key !== "custom");

const presetOptions = computed(() => [
  ...quickTimePresets.map((item) => ({ value: item.key, label: item.label })),
  { value: "custom", label: "自定义" },
]);

function onPresetChange(event: { target: { value: TimePreset } }) {
  props.filterState.setPreset(event.target.value);
}

function onPresetSelectChange(value: TimePreset) {
  props.filterState.setPreset(value);
}

function onCustomRangeChange(value: [Dayjs, Dayjs] | null) {
  if (!value || value.length !== 2) return;
  props.filterState.setCustomRange(value);
}

function openEditor() {
  props.filterState.openEditor(
    props.filterState.appliedConditions.value.length
      ? props.filterState.appliedConditions.value
      : undefined,
  );
}

function onEditorOpenChange(open: boolean) {
  if (!open) props.filterState.closeEditor();
}

function applyEditor() {
  props.filterState.applyDraft();
}

function clearFilters() {
  props.filterState.clearAppliedFilters();
}

function removeApplied(index: number) {
  props.filterState.removeAppliedCondition(index);
}

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
.log-filter-bar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.time-bar :deep(.ant-card-body) {
  padding: 10px 12px;
}

.time-bar-inner {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.time-bar-presets {
  min-width: 0;
}

.preset-select {
  width: 100%;
}

.preset-group {
  display: block;
  width: 100%;
}

.preset-group :deep(.ant-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  width: 100%;
}

.preset-group :deep(.ant-radio-button-wrapper) {
  flex: 0 1 auto;
  margin: 2px;
  height: 28px;
  line-height: 26px;
  padding-inline: 10px;
  font-size: 12px;
  border-radius: 6px !important;
  border-inline-start-width: 1px;
}

.preset-group :deep(.ant-radio-button-wrapper:not(:first-child)::before) {
  display: none;
}

.time-bar-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.custom-range {
  flex: 1 1 240px;
  min-width: 0;
  max-width: 100%;
}

.time-hint {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  word-break: break-all;
}

.refresh-btn {
  margin-left: auto;
  flex-shrink: 0;
}

@media (min-width: 1024px) {
  .time-bar-inner {
    flex-direction: row;
    align-items: center;
    gap: 12px;
  }

  .time-bar-presets {
    flex: 1 1 auto;
    min-width: 0;
  }

  .time-bar-meta {
    flex: 0 0 auto;
    max-width: 46%;
  }

  .custom-range {
    flex: 1 1 280px;
    max-width: 360px;
  }
}

@media (max-width: 1023px) {
  .time-bar-meta {
    width: 100%;
  }

  .refresh-btn {
    margin-left: 0;
  }

  .custom-range :deep(.ant-picker) {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .time-bar-meta {
    flex-direction: column;
    align-items: stretch;
  }

  .refresh-btn {
    width: 100%;
  }
}

.filter-bar-card :deep(.ant-card-body) {
  padding: 10px 14px;
}

.filter-bar-inner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.filter-icon {
  margin-top: 7px;
  color: #818fa2;
  font-size: 18px;
}

.filter-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.filter-tag {
  margin: 0;
  max-width: 100%;
  padding: 3px 6px;
}

.add-filter-btn,
.clear-filter-btn {
  padding-inline: 0;
}

.value-input {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cookie-arg-input {
  width: 100%;
}

.filter-editor {
  width: min(720px, calc(100vw - 48px));
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

.filter-editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
}

@media (max-width: 900px) {
  .filter-editor-row {
    grid-template-columns: 1fr;
  }

  .remove-btn {
    justify-self: end;
  }
}
</style>
