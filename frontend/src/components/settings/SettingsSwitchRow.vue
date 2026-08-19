<template>
  <div
    class="settings-switch-row"
    :class="{ 'is-warning': warning && checked, 'is-disabled': disabled }"
    role="button"
    tabindex="0"
    @click="toggle"
    @keydown.enter.prevent="toggle"
    @keydown.space.prevent="toggle"
  >
    <div class="settings-switch-row__text">
      <div class="settings-switch-row__title">
        <span v-if="warning && checked" class="settings-switch-row__dot" aria-hidden="true" />
        {{ title }}
      </div>
      <div v-if="description" class="settings-switch-row__desc">{{ description }}</div>
    </div>
    <div class="settings-switch-row__switch" @click.stop="toggle">
      <a-switch :checked="checked" :disabled="disabled" tabindex="-1" />
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  title: string;
  description?: string;
  checked: boolean;
  disabled?: boolean;
  warning?: boolean;
}>();

const emit = defineEmits<{
  "update:checked": [value: boolean];
}>();

function toggle() {
  if (props.disabled) return;
  emit("update:checked", !props.checked);
}
</script>

<style scoped>
.settings-switch-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  min-height: 44px;
  padding: 12px 14px;
  border: 1px solid var(--fs-border);
  border-radius: var(--fs-radius-md);
  background: var(--fs-bg-surface);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.settings-switch-row:hover:not(.is-disabled) {
  border-color: color-mix(in srgb, var(--fs-color-primary) 35%, var(--fs-border));
}

.settings-switch-row.is-warning {
  border-color: color-mix(in srgb, #b45309 45%, var(--fs-border));
  background: color-mix(in srgb, #b45309 6%, var(--fs-bg-surface));
}

.settings-switch-row.is-disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.settings-switch-row__text {
  flex: 1;
  min-width: 0;
}

.settings-switch-row__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--fs-text-primary);
}

.settings-switch-row__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #b45309;
  flex-shrink: 0;
}

.settings-switch-row__desc {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--fs-text-muted);
}

.settings-switch-row__switch {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.settings-switch-row__switch :deep(.ant-switch) {
  pointer-events: none;
}
</style>
