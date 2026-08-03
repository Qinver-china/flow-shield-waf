<template>
  <a-popover
    v-model:open="open"
    trigger="click"
    placement="bottomLeft"
    overlay-class-name="log-filter-field-picker-popover"
    :get-popup-container="getPopupContainer"
  >
    <button type="button" class="field-picker-trigger" :title="selectedLabel">
      <span class="field-picker-trigger-label">{{ selectedLabel }}</span>
      <down-outlined class="field-picker-trigger-icon" />
    </button>
    <template #content>
      <div class="field-picker-panel">
        <section v-for="group in groups" :key="group.label" class="dimension-group">
          <div class="dimension-group-title">{{ group.label }}</div>
          <div class="dimension-grid">
            <button
              v-for="field in group.fields"
              :key="field.key"
              type="button"
              class="dimension-btn"
              :class="{ active: modelValue === field.key }"
              :title="field.placeholder || field.label"
              @click="selectField(field.key)"
            >
              {{ field.label }}
            </button>
          </div>
        </section>
      </div>
    </template>
  </a-popover>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { DownOutlined } from "@ant-design/icons-vue";
import { findLogFilterField, logDetailFilterGroups, type LogFilterFieldDef } from "./constants";

const props = defineProps<{
  modelValue: string;
  groups?: { label: string; fields: LogFilterFieldDef[] }[];
  getPopupContainer?: (triggerNode: HTMLElement) => HTMLElement;
}>();

const emit = defineEmits<{
  "update:modelValue": [string];
  change: [string];
}>();

const open = ref(false);

const groups = computed(() => props.groups || logDetailFilterGroups);

const selectedLabel = computed(() => findLogFilterField(props.modelValue)?.label || "选择字段");

function selectField(key: string) {
  emit("update:modelValue", key);
  emit("change", key);
  open.value = false;
}
</script>

<style scoped>
.field-picker-trigger {
  appearance: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
  min-height: 32px;
  margin: 0;
  padding: 4px 11px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--fs-text);
  background: var(--fs-bg-surface);
  border: 1px solid var(--fs-border);
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.field-picker-trigger:hover {
  border-color: #4096ff;
}

.field-picker-trigger-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.field-picker-trigger-icon {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--fs-border);
}

.field-picker-panel {
  width: min(320px, calc(100vw - 48px));
  max-height: min(420px, 60vh);
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 2px;
}

.dimension-group + .dimension-group {
  margin-top: 12px;
}

.dimension-group-title {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 0.02em;
  margin-bottom: 6px;
}

.dimension-grid {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.dimension-btn {
  flex: 1 0 calc(30% - 6px);
  appearance: none;
  margin: 0;
  padding: 5px;
  font-size: 12px;
  line-height: 1.35;
  border: 1px solid #6a6c6e30;
  border-radius: 6px;
  background: #c2c2c20d;
  color: var(--fs-text-secondary);
  cursor: pointer;
  text-align: center;
  transition:
    border-color 0.15s,
    background 0.15s,
    color 0.15s,
    box-shadow 0.15s;
}

.dimension-btn:hover {
  border-color: #36a9df77;
  color: #048fdb;
}

.dimension-btn.active {
  border-color: #38bdf894;
  background: #29a9ff12;
  color: #048fdb;
  font-weight: 600;
}

.dimension-btn:focus-visible {
  outline: 2px solid #38bdf8;
  outline-offset: 1px;
}
</style>

<style>
.log-filter-field-picker-popover .ant-popover-inner {
  padding: 10px 12px;
}
</style>
