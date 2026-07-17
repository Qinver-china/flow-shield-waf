<template>
  <div class="fs-data-table">
    <a-table
      :columns="columns"
      :data-source="dataSource"
      :loading="loading"
      :pagination="pagination"
      :row-selection="rowSelection"
      :row-key="rowKey"
      :size="size"
      :scroll="scroll"
      @change="(...args) => emit('change', ...args)"
    >
      <template v-for="(_, name) in $slots" #[name]="slotData">
        <slot :name="name" v-bind="slotData ?? {}" />
      </template>
    </a-table>

    <table-batch-bar
      v-if="batchEnabled"
      :count="selectedCount"
      :processing="batchProcessing"
      :actions="availableActions()"
      :mode-options="modeOptions"
      @execute="onBatchExecute"
      @clear="clearSelection"
    />

    <batch-edit-drawer
      v-if="hasBatchEdit"
      v-model:open="batchEditOpen"
      :count="selectedCount"
      :fields="editFields"
      :loading="batchProcessing"
      @submit="batchUpdate"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import BatchEditDrawer from "@/components/BatchEditDrawer.vue";
import TableBatchBar from "@/components/TableBatchBar.vue";
import { useTableBatch } from "@/composables/useTableBatch";
import type { BatchActionKey, BatchConfig } from "@/types/batch";

const props = withDefaults(
  defineProps<{
    columns: any[];
    dataSource: any[];
    loading?: boolean;
    pagination?: any;
    apiBase: string;
    batch?: BatchConfig | false;
    hasEnabledColumn?: boolean;
    rowKey?: string;
    size?: "small" | "middle" | "large";
    scroll?: Record<string, unknown>;
  }>(),
  {
    rowKey: "id",
    size: "middle",
    hasEnabledColumn: false,
  },
);

const emit = defineEmits<{
  change: [pagination: any, filters: any, sorter: any];
  refresh: [];
}>();

const rows = computed(() => props.dataSource ?? []);

const batchConfig = computed<BatchConfig | undefined>(() =>
  props.batch === false ? undefined : props.batch,
);

const hasEnabled = computed(() => props.hasEnabledColumn);

const {
  selectedCount,
  batchProcessing,
  batchEditOpen,
  batchEnabled,
  modeOptions,
  editFields,
  hasBatchEdit,
  rowSelection,
  clearSelection,
  batchEnable,
  batchSwitchMode,
  batchDelete,
  batchUpdate,
  availableActions,
} = useTableBatch({
  apiBase: props.apiBase,
  rows,
  batch: batchConfig,
  hasEnabledColumn: hasEnabled,
  onRefresh: () => emit("refresh"),
});

function onBatchExecute(action: BatchActionKey, mode?: string) {
  if (action === "edit") {
    batchEditOpen.value = true;
    return;
  }
  if (action === "enable") {
    batchEnable(true);
    return;
  }
  if (action === "disable") {
    batchEnable(false);
    return;
  }
  if (action === "switch_mode" && mode) {
    batchSwitchMode(mode);
    return;
  }
  if (action === "delete") {
    batchDelete();
  }
}
</script>
