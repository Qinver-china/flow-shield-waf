<template>
  <div
    class="stat-card"
    :class="{ 'stat-card-lg': large, 'stat-card-clickable': clickable }"
    :style="{ '--accent': color }"
    :role="clickable ? 'button' : undefined"
    :tabindex="clickable ? 0 : undefined"
    @click="onClick"
    @keydown.enter="onClick"
  >
    <div class="stat-card-top">
      <div v-if="icon" class="stat-card-icon">
        <component :is="icon" />
      </div>
      <div class="stat-card-main">
        <div class="stat-card-value" :style="valueColor ? { color: valueColor } : undefined">
          {{ value }}
          <span v-if="delta !== undefined" class="stat-card-delta" :class="deltaClass">
            {{ deltaPrefix }}{{ Math.abs(delta).toFixed(1) }}%
          </span>
        </div>
        <div class="stat-card-label">{{ label }}</div>
      </div>
    </div>
    <div v-if="sub" class="stat-card-sub">{{ sub }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Component } from "vue";

const props = defineProps<{
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
  valueColor?: string;
  icon?: Component;
  large?: boolean;
  delta?: number;
  clickable?: boolean;
}>();

const emit = defineEmits<{ click: [] }>();

function onClick() {
  if (props.clickable) emit("click");
}

const deltaClass = computed(() => {
  if (props.delta === undefined) return "";
  if (props.delta > 0) return "up";
  if (props.delta < 0) return "down";
  return "flat";
});

const deltaPrefix = computed(() => {
  if (props.delta === undefined) return "";
  if (props.delta > 0) return "+";
  if (props.delta < 0) return "-";
  return "";
});
</script>

<style scoped>
.stat-card {
  --accent: var(--fs-color-primary);
  height: 100%;
  padding: 14px;
  border-radius: var(--fs-radius-md);
  background: var(--fs-bg-surface);
  border: 1px solid var(--fs-border);
  box-shadow: var(--fs-shadow-sm);
  border-top: 3px solid var(--accent);
  transition: box-shadow var(--fs-transition), transform var(--fs-transition);
}

.stat-card:hover {
  box-shadow: var(--fs-shadow-md);
}

.stat-card-clickable {
  cursor: pointer;
}

.stat-card-clickable:hover {
  transform: translateY(-1px);
}

.stat-card-clickable:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.stat-card-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-card-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 12%, var(--fs-bg-surface));
}

.stat-card-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--fs-text-primary);
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}

.stat-card-lg .stat-card-value {
  font-size: 28px;
}

.stat-card-delta {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 999px;
}

.stat-card-delta.up {
  color: var(--fs-color-danger);
  background: color-mix(in srgb, var(--fs-color-danger) 12%, transparent);
}

.stat-card-delta.down {
  color: var(--fs-color-accent);
  background: var(--fs-color-accent-muted);
}

.stat-card-delta.flat {
  color: var(--fs-text-muted);
  background: var(--fs-bg-muted);
}

.stat-card-label {
  margin-top: 2px;
  font-size: 13px;
  color: var(--fs-text-secondary);
}

.stat-card-sub {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--fs-border);
  font-size: 12px;
  color: var(--fs-text-muted);
}
</style>
