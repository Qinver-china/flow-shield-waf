<template>
  <div class="fs-data-table">
    <a-table
      v-if="!isMobile"
      :columns="columns"
      :data-source="dataSource"
      :loading="loading"
      :pagination="resolvedPagination"
      :row-selection="rowSelection"
      :row-key="rowKey"
      :size="size"
      :scroll="resolvedScroll"
      :show-sorter-tooltip="false"
      bordered
      @change="(...args) => emit('change', ...args)"
    >
      <template v-for="(_, name) in $slots" #[name]="slotData">
        <slot :name="name" v-bind="slotData ?? {}" />
      </template>
    </a-table>

    <fs-mobile-table-cards
      v-else
      :columns="columns"
      :data-source="dataSource"
      :loading="loading"
      :pagination="resolvedPagination"
      :row-key="rowKey"
      :title-key="mobileTitleKey"
      :exclude-keys="mobileExcludeKeys"
      :selectable="batchEnabled"
      :selected-keys="selectedRowKeys"
      @change="(pag) => emit('change', pag, {}, {})"
      @select="onMobileSelect"
    >
      <template v-if="hasEnabledColumn" #headExtra="{ record }">
        <slot name="bodyCell" :column="enabledColumn" :record="record" :text="record.enabled" />
      </template>
      <template #cell="slotData">
        <slot name="bodyCell" v-bind="slotData" />
      </template>
    </fs-mobile-table-cards>

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
import FsMobileTableCards from "@/components/FsMobileTableCards.vue";
import TableBatchBar from "@/components/TableBatchBar.vue";
import { useResponsivePagination } from "@/composables/useResponsivePagination";
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
    mobileTitleKey?: string;
    mobileExcludeKeys?: string[];
  }>(),
  {
    rowKey: "id",
    size: "middle",
    hasEnabledColumn: false,
    mobileExcludeKeys: () => ["actions", "enabled"],
  },
);

const emit = defineEmits<{
  change: [pagination: any, filters: any, sorter: any];
  refresh: [];
}>();

const rows = computed(() => props.dataSource ?? []);
const { isMobile, withPaginationSize } = useResponsivePagination();

const resolvedPagination = computed(() => withPaginationSize(props.pagination as any));

const resolvedScroll = computed(() => {
  if (props.scroll) return props.scroll;
  return { x: "max-content" as const };
});

const enabledColumn = computed(() => ({ key: "enabled", title: "启用", dataIndex: "enabled" }));

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
  toggleMobileRow,
} = useTableBatch({
  apiBase: props.apiBase,
  rows,
  batch: batchConfig,
  hasEnabledColumn: hasEnabled,
  onRefresh: () => emit("refresh"),
});

const selectedRowKeys = computed(() => rowSelection.value?.selectedRowKeys ?? []);

function onMobileSelect(key: string | number, checked: boolean) {
  toggleMobileRow(Number(key), checked);
}

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
