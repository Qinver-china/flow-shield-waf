<template>
  <div class="page-shell">
    <div class="page-shell-head">
      <div class="page-shell-meta">
        <h2 class="page-shell-title">{{ title }}</h2>
        <p v-if="description" class="page-shell-desc">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="page-shell-actions">
        <slot name="actions" />
      </div>
    </div>
    <div v-if="$slots.default" class="page-shell-body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<style scoped>
.page-shell {
  display: flex;
  flex-direction: column;
  gap: var(--fs-space-md);
}

.page-shell-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--fs-space-md);
  flex-wrap: wrap;
}

.page-shell-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--fs-text-primary);
  line-height: 1.25;
}

.page-shell-desc {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--fs-text-secondary);
  max-width: 640px;
}

.page-shell-actions {
  display: flex;
  align-items: center;
  gap: var(--fs-space-sm);
  flex-shrink: 0;
}

.page-shell-body {
  display: flex;
  flex-direction: column;
  gap: var(--fs-space-md);
}

@media (max-width: 767px) {
  .page-shell-title {
    font-size: 18px;
  }

  .page-shell-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
