<template>
  <fs-form-drawer
    v-model:open="openModel"
    title="批量编辑"
    :subtitle="`已选 ${count} 项`"
    mode="edit"
    :width="560"
    :confirm-loading="loading"
    ok-text="应用到选中项"
    @ok="onSubmit"
  >
    <a-alert
      type="info"
      show-icon
      message="仅勾选「应用」的字段会更新到所有选中项，未勾选的字段保持不变。"
      style="margin-bottom: 16px"
    />
    <a-form layout="vertical">
      <div v-for="field in fields" :key="field.key" class="batch-edit-field">
        <a-checkbox v-model:checked="applyFlags[field.key]">
          {{ field.label }}
        </a-checkbox>
        <div class="batch-edit-control">
          <template v-if="field.type === 'switch'">
            <a-select
              v-model:value="values[field.key]"
              style="width: 100%"
              :disabled="!applyFlags[field.key]"
              placeholder="选择状态"
            >
              <a-select-option :value="true">启用</a-select-option>
              <a-select-option :value="false">停用</a-select-option>
            </a-select>
          </template>
          <template v-else-if="field.type === 'select'">
            <a-select
              v-model:value="values[field.key]"
              style="width: 100%"
              :disabled="!applyFlags[field.key]"
              :placeholder="field.placeholder || '请选择'"
              :options="field.options"
            />
          </template>
          <template v-else-if="field.type === 'number'">
            <a-input-number
              v-model:value="values[field.key]"
              style="width: 100%"
              :min="field.min ?? 1"
              :disabled="!applyFlags[field.key]"
              :placeholder="field.placeholder"
            />
          </template>
          <template v-else-if="field.type === 'site_ids'">
            <site-select
              v-model:value="values[field.key]"
              :readonly="!applyFlags[field.key]"
            />
          </template>
        </div>
      </div>
    </a-form>
  </fs-form-drawer>
</template>

<script setup lang="ts">
import { reactive, watch } from "vue";
import FsFormDrawer from "@/components/FsFormDrawer.vue";
import SiteSelect from "@/components/SiteSelect.vue";
import type { BatchEditField } from "@/types/batch";

const props = defineProps<{
  count: number;
  fields: BatchEditField[];
  loading?: boolean;
}>();

const emit = defineEmits<{
  "update:open": [value: boolean];
  submit: [payload: Record<string, unknown>];
}>();

const openModel = defineModel<boolean>("open", { required: true });

const applyFlags = reactive<Record<string, boolean>>({});
const values = reactive<Record<string, unknown>>({});

function resetForm() {
  for (const field of props.fields) {
    applyFlags[field.key] = false;
    values[field.key] = field.type === "site_ids" ? [] : undefined;
  }
}

watch(
  openModel,
  (isOpen) => {
    if (isOpen) resetForm();
  },
);

watch(
  () => props.fields,
  () => resetForm(),
  { immediate: true },
);

function onSubmit() {
  const payload: Record<string, unknown> = {};
  for (const field of props.fields) {
    if (!applyFlags[field.key]) continue;
    const value = values[field.key];
    if (value === undefined || value === null) continue;
    if (field.type === "site_ids" && Array.isArray(value) && !value.length) {
      payload[field.key] = [];
      continue;
    }
    payload[field.key] = value;
  }
  emit("submit", payload);
}
</script>

<style scoped>
.batch-edit-field {
  margin-bottom: 16px;
}

.batch-edit-control {
  margin-top: 8px;
  padding-left: 24px;
}
</style>
