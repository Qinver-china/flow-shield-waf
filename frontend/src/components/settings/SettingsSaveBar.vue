<template>
  <div v-if="visible" class="settings-save-bar">
    <span class="settings-save-bar__hint" :class="{ 'is-dirty': dirty }">
      {{ dirty ? "有未保存的更改" : "暂无更改" }}
    </span>
    <a-button type="primary" size="large" :loading="loading" :disabled="!dirty || loading" @click="emit('save')">
      {{ label }}
    </a-button>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    visible?: boolean;
    dirty?: boolean;
    loading?: boolean;
    label?: string;
  }>(),
  {
    visible: true,
    dirty: false,
    loading: false,
    label: "保存",
  },
);

const emit = defineEmits<{
  save: [];
}>();
</script>

<style scoped>
.settings-save-bar {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  padding: 12px 16px;
  border: 1px solid var(--fs-border);
  border-radius: var(--fs-radius-md);
  background: var(--fs-bg-surface);
  box-shadow: var(--fs-shadow-sm);
}

.settings-save-bar__hint {
  font-size: 13px;
  color: var(--fs-text-muted);
}

.settings-save-bar__hint.is-dirty {
  color: rgb(223, 115, 33);
}

@media (max-width: 767px) {
  .settings-save-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .settings-save-bar :deep(.ant-btn) {
    min-height: 44px;
  }

  .settings-save-bar__hint {
    text-align: center;
  }
}
</style>
