<template>
  <a-popover
    v-model:open="open"
    trigger="click"
    :placement="triggerVariant === 'card' ? 'bottom' : 'bottomRight'"
    overlay-class-name="log-stats-dimension-picker-popover"
    :class="{ 'dimension-picker--card': triggerVariant === 'card' }"
  >
    <button
      type="button"
      class="dimension-picker-trigger"
      :class="{ 'dimension-picker-trigger--card': triggerVariant === 'card' }"
      :title="selectedLabel"
    >
      <template v-if="triggerVariant === 'card'">
        <span class="dimension-card-label">{{ label }}</span>
        <span class="dimension-card-value">
          <span class="dimension-card-name">{{ selectedLabel }}</span>
          <down-outlined class="dimension-card-icon" />
        </span>
      </template>
      <template v-else>
        <span class="dimension-picker-trigger-label">{{ selectedLabel }}</span>
        <down-outlined class="dimension-picker-trigger-icon" />
      </template>
    </button>
    <template #content>
      <div class="dimension-picker-panel">
        <section v-for="group in statsDimensionGroups" :key="group.label" class="dimension-group">
          <div class="dimension-group-title">{{ group.label }}</div>
          <div class="dimension-grid">
            <button
              v-for="item in group.items"
              :key="item.key"
              type="button"
              class="dimension-btn"
              :class="{ active: modelValue === item.key }"
              :title="item.desc"
              @click="selectDimension(item.key)"
            >
              {{ item.label }}
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
import { statsDimensionGroups, statsDimensions, type StatsDimension } from "./constants";

const props = withDefaults(
  defineProps<{
    modelValue: StatsDimension;
    triggerVariant?: "button" | "card";
    label?: string;
  }>(),
  {
    triggerVariant: "button",
    label: "统计维度",
  },
);

const emit = defineEmits<{
  change: [StatsDimension];
}>();

const open = ref(false);

const selectedLabel = computed(
  () => statsDimensions.find((item) => item.key === props.modelValue)?.label || "选择维度",
);

function selectDimension(key: StatsDimension) {
  open.value = false;
  if (key === props.modelValue) return;
  emit("change", key);
}
</script>

<style scoped>
.dimension-picker--card {
  display: block;
  width: 100%;
}

.dimension-picker-trigger {
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  min-width: 0;
  max-width: 100%;
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
  transition: border-color 0.2s, background 0.2s;
}

.dimension-picker-trigger:hover {
  border-color: #4096ff;
}

.dimension-picker-trigger-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.dimension-picker-trigger-icon {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--fs-border);
}

.dimension-picker-trigger--card {
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--fs-bg-surface);
  border: 1px solid var(--fs-border);
}

.dimension-picker-trigger--card:hover {
  border-color: color-mix(in srgb, var(--fs-color-primary) 35%, var(--fs-border));
  background: color-mix(in srgb, var(--fs-color-primary) 4%, var(--fs-bg-surface));
}

.dimension-picker-trigger--card:focus-visible {
  outline: 2px solid var(--fs-color-info);
  outline-offset: 1px;
}

.dimension-card-label {
  flex-shrink: 0;
  font-weight: 500;
  color: var(--fs-text);
}

.dimension-card-value {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  min-width: 0;
  margin-left: auto;
}

.dimension-card-name {
  color: var(--fs-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dimension-card-icon {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--fs-text-muted);
}

.dimension-picker-panel {
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
.log-stats-dimension-picker-popover .ant-popover-inner {
  padding: 10px 12px;
}
</style>
