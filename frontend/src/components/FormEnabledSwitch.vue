<template>
  <div class="form-enabled-switch" :class="{ 'is-readonly': readonly }">
    <span class="form-enabled-switch__label">启用</span>
    <a-switch
      :checked="checked"
      :disabled="readonly"
      :loading="loading"
      @update:checked="onChange"
    />
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  checked?: boolean;
  readonly?: boolean;
  loading?: boolean;
  /** 查看模式下为 true：切换后立即触发 immediate-change，由父级持久化 */
  immediate?: boolean;
}>();

const emit = defineEmits<{
  "update:checked": [boolean];
  "immediate-change": [boolean];
}>();

function onChange(value: boolean) {
  if (props.readonly) return;
  emit("update:checked", value);
  if (props.immediate) {
    emit("immediate-change", value);
  }
}
</script>

<style scoped>
.form-enabled-switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  border-radius: var(--fs-radius-sm);
  background: var(--fs-bg-muted);
  border: 1px solid var(--fs-border);
  white-space: nowrap;
}

.form-enabled-switch__label {
  font-size: 13px;
  font-weight: 600;
  color: var(--fs-text-secondary);
}

.form-enabled-switch.is-readonly {
  opacity: 0.92;
}
</style>
