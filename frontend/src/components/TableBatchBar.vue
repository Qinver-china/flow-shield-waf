<template>
  <transition name="batch-bar">
    <div v-if="count > 0" class="table-batch-bar">
      <div class="table-batch-bar-inner fs-card">
        <span class="table-batch-bar-count">已选择 <strong>{{ count }}</strong> 项</span>

        <a-select
          v-model:value="selectedAction"
          class="table-batch-bar-action"
          placeholder="选择批量操作"
          :options="actionOptions"
          :disabled="processing"
        />

        <a-select
          v-if="selectedAction === 'switch_mode'"
          v-model:value="modeValue"
          class="table-batch-bar-mode"
          placeholder="选择目标模式"
          :options="modeOptions"
          :disabled="processing"
        />

        <a-button
          type="primary"
          :loading="processing"
          :disabled="!canExecute"
          @click="onExecute"
        >
          执行
        </a-button>

        <a-button type="text" :disabled="processing" @click="emit('clear')">
          取消选择
        </a-button>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { BatchActionKey } from "@/types/batch";

const props = defineProps<{
  count: number;
  processing?: boolean;
  actions: BatchActionKey[];
  modeOptions?: { label: string; value: string }[];
}>();

const emit = defineEmits<{
  execute: [action: BatchActionKey, mode?: string];
  clear: [];
}>();

const actionLabels: Record<BatchActionKey, string> = {
  edit: "批量编辑",
  enable: "批量启用",
  disable: "批量停用",
  switch_mode: "批量切换模式",
  delete: "批量删除",
};

const selectedAction = ref<BatchActionKey>();
const modeValue = ref<string>();

const actionOptions = computed(() =>
  props.actions.map((value) => ({
    value,
    label: actionLabels[value],
  })),
);

const canExecute = computed(() => {
  if (!selectedAction.value) return false;
  if (selectedAction.value === "switch_mode") return Boolean(modeValue.value);
  return true;
});

watch(
  () => props.count,
  (count) => {
    if (!count) {
      selectedAction.value = undefined;
      modeValue.value = undefined;
    }
  },
);

watch(selectedAction, (action) => {
  if (action !== "switch_mode") {
    modeValue.value = undefined;
  }
});

function onExecute() {
  if (!selectedAction.value || !canExecute.value) return;
  emit("execute", selectedAction.value, modeValue.value);
}
</script>

<style scoped>
.table-batch-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 24px;
  z-index: 100;
  display: flex;
  justify-content: center;
  padding: 0 16px;
  pointer-events: none;
}

.table-batch-bar-inner {
  pointer-events: auto;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 16px;
  max-width: 960px;
  width: 100%;
  box-shadow: var(--fs-shadow-lg);
}

.table-batch-bar-count {
  font-size: 13px;
  color: var(--fs-text-secondary);
  white-space: nowrap;
}

.table-batch-bar-count strong {
  color: var(--fs-color-primary);
  font-weight: 700;
}

.table-batch-bar-action {
  width: 180px;
}

.table-batch-bar-mode {
  width: 200px;
}

.batch-bar-enter-active,
.batch-bar-leave-active {
  transition: opacity var(--fs-transition), transform var(--fs-transition);
}

.batch-bar-enter-from,
.batch-bar-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

@media (max-width: 767px) {
  .table-batch-bar {
    bottom: 12px;
  }

  .table-batch-bar-inner {
    flex-direction: column;
    align-items: stretch;
  }

  .table-batch-bar-action,
  .table-batch-bar-mode {
    width: 100%;
  }
}
</style>
