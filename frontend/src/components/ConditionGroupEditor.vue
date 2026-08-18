<template>
  <div :class="['cond-group', { 'cond-group-nested': depth > 0 }, 'logic-type-' + group.logic]">
    <div class="logic-row">
      <div class="logic-left">
        <span v-if="depth > 0" class="group-tag">条件组</span>
        <span>满足以下</span>
        <a-select v-if="!readonly" v-model:value="group.logic" class="logic-select" size="small">
          <a-select-option value="and">全部 (AND)</a-select-option>
          <a-select-option value="or">任一 (OR)</a-select-option>
        </a-select>
        <strong v-else>{{ logicLabel(group.logic) }}</strong>
        <span>条件：</span>
      </div>
      <div v-if="!readonly" class="logic-actions">
        <a-button size="small" type="primary" :icon="h(PlusOutlined)" @click="addLeaf">条件</a-button>
        <a-button v-if="canNest" size="small" class="add-group-btn" :icon="h(PlusOutlined)" @click="addGroup">条件组
        </a-button>
        <a-button v-if="depth > 0" danger type="text" :icon="h(DeleteOutlined)" @click="$emit('remove')">
        </a-button>
      </div>
    </div>
    <div v-if="group.conditions.length" class="cond-children">
      <template v-for="(node, idx) in group.conditions" :key="idx">
        <condition-leaf-row v-if="node.kind === 'leaf'" :row="node" :catalog="catalog" :field-map="fieldMap"
          :operators="operators" :ip-group-options="ipGroupOptions" :ip-group-label="ipGroupLabel" :readonly="readonly"
          @remove="removeChild(idx)" />
        <condition-group-editor v-else :group="node" :depth="depth + 1" :catalog="catalog" :field-map="fieldMap"
          :operators="operators" :ip-group-options="ipGroupOptions" :ip-group-label="ipGroupLabel" :readonly="readonly"
          @remove="removeChild(idx)" />
      </template>
    </div>

    <a-empty v-else :description="depth === 0 ? '暂无条件（留空表示匹配全部请求）' : '该条件组为空'" :image-style="{ height: '40px' }" />
  </div>
</template>

<script setup lang="ts">
import { computed, h } from "vue";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons-vue";
import ConditionLeafRow from "@/components/ConditionLeafRow.vue";
import type { Category, Field, UiGroup } from "@/composables/useConditionModel";
import type { IpGroupOption } from "@/composables/useIpGroupOptions";

import {
  MAX_GROUP_DEPTH,
  emptyGroup,
  emptyLeaf,
  logicLabel,
} from "@/composables/useConditionModel";

const props = defineProps<{
  group: UiGroup;
  depth?: number;
  catalog: Category[];
  fieldMap: Record<string, Field>;
  operators: Record<string, string>;
  ipGroupOptions?: IpGroupOption[];
  ipGroupLabel?: (id: string) => string;
  readonly?: boolean;
}>();

defineEmits<{ remove: [] }>();

const depth = computed(() => props.depth ?? 0);
const canNest = computed(() => depth.value < MAX_GROUP_DEPTH - 1);

function addLeaf() {
  props.group.conditions.push(emptyLeaf());
}

function addGroup() {
  props.group.conditions.push(emptyGroup());
}

function removeChild(idx: number) {
  props.group.conditions.splice(idx, 1);
}
</script>

<script lang="ts">
export default {
  name: "ConditionGroupEditor",
};
</script>

<style scoped>
.cond-group-nested {
  border: 1px dashed rgb(203, 213, 225, 0.1);
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 8px;
  background: rgba(79, 97, 131, 0.03);
}

.logic-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.logic-left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.logic-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.add-group-btn {
  color: #2563eb;
  border-color: rgba(104, 174, 255, 0.5);
}

.add-group-btn:hover {
  color: #1d4ed8;
  border-color: #60a5fa;
}

.logic-type-and {
  --fs-logic-type-color: color-mix(in srgb, #e9550a var(--fs-logic-type-color-ratio, 100%), #c92ce4);
}

.logic-type-or {
  --fs-logic-type-color: color-mix(in srgb, #09ae0e var(--fs-logic-type-color-ratio, 100%), #1a5edb);
}

.cond-children {
  padding-left: 8px;
  border-left: 1px solid color-mix(in srgb, var(--fs-logic-type-color) 60%, transparent);
}

.group-tag {
  display: inline-block;
  padding: 0 6px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--fs-logic-type-color) 10%, transparent);
  color: var(--fs-logic-type-color);
  font-size: 12px;
  line-height: 20px;
}

.logic-select :deep(.ant-select-selection-item) {
  color: var(--fs-logic-type-color);
}

.cond-children>.cond-group {
  --fs-logic-type-color-ratio: 63%;
}

.cond-children>.cond-group .cond-children>.cond-group {
  --fs-logic-type-color-ratio: 33%;
}

.cond-children>.cond-group .cond-children>.cond-group .cond-children>.cond-group {
  --fs-logic-type-color-ratio: 0%;
}

</style>
