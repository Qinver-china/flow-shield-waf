import { computed, ref, type ComputedRef, type Ref } from "vue";
import { Modal, message } from "ant-design-vue";
import { api } from "@/api";
import type { BatchActionKey, BatchConfig } from "@/types/batch";

interface UseTableBatchOptions {
  apiBase: string;
  rows: Ref<Array<{ id: number }>>;
  batch: ComputedRef<BatchConfig | undefined>;
  hasEnabledColumn: ComputedRef<boolean>;
  onRefresh: () => void | Promise<void>;
}

export function useTableBatch(options: UseTableBatchOptions) {
  const selectedRowKeys = ref<number[]>([]);
  const batchProcessing = ref(false);
  const batchEditOpen = ref(false);
  const pendingMode = ref<string>();

  const batchEnabled = computed(() => {
    if (options.batch.value === undefined) return false;
    return options.batch.value.enabled !== false;
  });

  const enableToggle = computed(
    () => options.batch.value?.enableToggle ?? options.hasEnabledColumn.value ?? false,
  );

  const allowDelete = computed(() => options.batch.value?.allowDelete !== false);

  const modeOptions = computed(() => options.batch.value?.modeOptions ?? []);

  const modeField = computed(() => options.batch.value?.modeField ?? "mode");

  const hasModeSwitch = computed(() => modeOptions.value.length > 0);

  const editFields = computed(() => options.batch.value?.editFields ?? []);

  const hasBatchEdit = computed(() => editFields.value.length > 0);

  const selectedCount = computed(() => selectedRowKeys.value.length);

  const rowSelection = computed(() => {
    if (!batchEnabled.value) return undefined;
    return {
      selectedRowKeys: selectedRowKeys.value,
      onChange: (keys: Array<string | number>) => {
        selectedRowKeys.value = keys.map(Number);
      },
      preserveSelectedRowKeys: true,
    };
  });

  function clearSelection() {
    selectedRowKeys.value = [];
    pendingMode.value = undefined;
  }

  function toggleMobileRow(id: number, checked: boolean) {
    if (checked) {
      if (!selectedRowKeys.value.includes(id)) {
        selectedRowKeys.value = [...selectedRowKeys.value, id];
      }
    } else {
      selectedRowKeys.value = selectedRowKeys.value.filter((key) => key !== id);
    }
  }

  function isMobileRowSelected(id: number) {
    return selectedRowKeys.value.includes(id);
  }

  async function runBatch(
    action: (id: number) => Promise<unknown>,
    successText: string,
  ) {
    if (!selectedRowKeys.value.length) return;
    batchProcessing.value = true;
    const ids = [...selectedRowKeys.value];
    const results = await Promise.allSettled(ids.map((id) => action(id)));
    const failed = results.filter((r) => r.status === "rejected").length;
    batchProcessing.value = false;
    if (failed === 0) {
      message.success(successText);
    } else if (failed === ids.length) {
      message.error("批量操作失败");
    } else {
      message.warning(`部分成功：${ids.length - failed} 项完成，${failed} 项失败`);
    }
    clearSelection();
    await options.onRefresh();
  }

  async function batchEnable(enabled: boolean) {
    await runBatch(
      (id) => api.put(`${options.apiBase}/${id}`, { enabled }),
      enabled ? "已批量启用" : "已批量停用",
    );
  }

  async function batchSwitchMode(mode: string) {
    const field = modeField.value;
    await runBatch(
      (id) => api.put(`${options.apiBase}/${id}`, { [field]: mode }),
      "已批量切换模式",
    );
  }

  async function batchDelete() {
    if (!selectedRowKeys.value.length) return;
    Modal.confirm({
      title: "确认批量删除",
      content: `确定删除选中的 ${selectedRowKeys.value.length} 项？此操作不可恢复。`,
      okText: "删除",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        await runBatch((id) => api.del(`${options.apiBase}/${id}`), "已批量删除");
      },
    });
  }

  async function batchUpdate(payload: Record<string, unknown>) {
    const keys = Object.keys(payload);
    if (!keys.length) {
      message.warning("请至少修改一项");
      return;
    }
    await runBatch(
      (id) => api.put(`${options.apiBase}/${id}`, payload),
      "批量编辑已应用",
    );
    batchEditOpen.value = false;
  }

  function availableActions(): BatchActionKey[] {
    const actions: BatchActionKey[] = [];
    if (hasBatchEdit.value) actions.push("edit");
    if (enableToggle.value) {
      actions.push("enable", "disable");
    }
    if (hasModeSwitch.value) actions.push("switch_mode");
    if (allowDelete.value) actions.push("delete");
    return actions;
  }

  return {
    selectedRowKeys,
    selectedCount,
    batchProcessing,
    batchEditOpen,
    pendingMode,
    batchEnabled,
    enableToggle,
    allowDelete,
    modeOptions,
    modeField,
    hasModeSwitch,
    editFields,
    hasBatchEdit,
    rowSelection,
    clearSelection,
    toggleMobileRow,
    isMobileRowSelected,
    batchEnable,
    batchSwitchMode,
    batchDelete,
    batchUpdate,
    availableActions,
  };
}
