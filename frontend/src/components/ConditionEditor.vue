<template>
  <div :class="readonly ? 'cond-view' : 'cond-editor'">
    <condition-group-editor
      :group="model"
      :catalog="catalog"
      :field-map="fieldMap"
      :operators="operators"
      :ip-group-options="ipGroupOptions"
      :ip-group-label="ipGroupLabel"
      :readonly="readonly"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { api } from "@/api";
import ConditionGroupEditor from "@/components/ConditionGroupEditor.vue";
import type { Category, Field, UiGroup } from "@/composables/useConditionModel";
import { useIpGroupOptions } from "@/composables/useIpGroupOptions";
import {
  emptyGroup,
  parseConditionTree,
  serializeTree,
} from "@/composables/useConditionModel";

const props = defineProps<{ value?: any; readonly?: boolean }>();
const emit = defineEmits<{ (e: "update:value", v: any): void }>();

const catalog = ref<Category[]>([]);
const operators = ref<Record<string, string>>({});
const fieldMap = ref<Record<string, Field>>({});

const model = reactive<UiGroup>(emptyGroup());
const { options: ipGroupOptions, labelFor: ipGroupLabel, load: loadIpGroups } = useIpGroupOptions();

function loadFromValue(v: any) {
  const parsed = parseConditionTree(v);
  model.logic = parsed.logic;
  model.conditions.splice(0, model.conditions.length, ...parsed.conditions);
}

function serialize() {
  return serializeTree(model, fieldMap.value);
}

watch(
  model,
  () => {
    if (!props.readonly) emit("update:value", serialize());
  },
  { deep: true },
);

watch(
  () => props.value,
  (v) => {
    if (v && JSON.stringify(serialize()) !== JSON.stringify(v)) loadFromValue(v);
  },
);

onMounted(async () => {
  const resp = await api.get("/api/v1/meta/fields");
  catalog.value = resp.data.categories;
  operators.value = resp.data.operators;
  const map: Record<string, Field> = {};
  for (const cat of catalog.value) for (const f of cat.fields) map[f.key] = f;
  fieldMap.value = map;
  await loadIpGroups();
  if (props.value) loadFromValue(props.value);
});
</script>

<style scoped>
.cond-view,
.cond-editor {
  border: 1px solid rgb(229, 231, 235, 0.1);
  border-radius: 8px;
  padding: 12px;
  background: rgba(78, 78, 78, 0.05);
  font-size: 13px;
}

.cond-view :deep(.ant-select),
.cond-editor :deep(.ant-select),
.cond-view :deep(.ant-input),
.cond-editor :deep(.ant-input),
.cond-view :deep(.ant-input-number),
.cond-editor :deep(.ant-input-number),
.cond-view :deep(.ant-btn),
.cond-editor :deep(.ant-btn),
.cond-view :deep(.ant-empty-description),
.cond-editor :deep(.ant-empty-description) {
  font-size: 13px;
}
</style>
