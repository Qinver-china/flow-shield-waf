<template>
  <a-popover
    v-model:open="open"
    trigger="click"
    placement="bottomLeft"
    overlay-class-name="cond-field-picker-popover"
    :arrow="false"
  >
    <template #content>
      <div class="cond-field-picker">
        <a-input
          v-model:value="query"
          allow-clear
          placeholder="搜索字段名称"
          class="cond-field-picker-search"
        />
        <div class="cond-field-picker-body">
          <div
            v-for="cat in filteredCatalog"
            :key="cat.name"
            class="cond-field-picker-group"
          >
            <div class="cond-field-picker-group-title">{{ cat.name }}</div>
            <div class="cond-field-picker-grid">
              <button
                v-for="field in cat.fields"
                :key="field.key"
                type="button"
                class="cond-field-picker-btn"
                :class="{ active: field.key === value }"
                @click="pick(field.key)"
              >
                {{ field.label }}
              </button>
            </div>
          </div>
          <a-empty v-if="!filteredCatalog.length" :image="false" description="无匹配字段" />
        </div>
      </div>
    </template>

    <button type="button" class="cond-field-picker-trigger" :class="{ placeholder: !value }">
      <span class="cond-field-picker-trigger-text">{{ displayLabel }}</span>
      <DownOutlined class="cond-field-picker-trigger-icon" />
    </button>
  </a-popover>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { DownOutlined } from "@ant-design/icons-vue";
import type { Category, Field } from "@/composables/useConditionModel";

const props = withDefaults(
  defineProps<{
    value?: string;
    catalog: Category[];
    fieldMap: Record<string, Field>;
    placeholder?: string;
  }>(),
  { placeholder: "字段" },
);

const emit = defineEmits<{
  (e: "update:value", value: string | undefined): void;
  (e: "change"): void;
}>();

const open = ref(false);
const query = ref("");

const displayLabel = computed(() => {
  if (!props.value) return props.placeholder;
  return props.fieldMap[props.value]?.label || props.value;
});

const filteredCatalog = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return props.catalog;

  return props.catalog
    .map((cat) => ({
      ...cat,
      fields: cat.fields.filter((field) => {
        const label = field.label.toLowerCase();
        const key = field.key.toLowerCase();
        return label.includes(q) || key.includes(q);
      }),
    }))
    .filter((cat) => cat.fields.length > 0);
});

function pick(fieldKey: string) {
  emit("update:value", fieldKey);
  emit("change");
  open.value = false;
}

watch(open, (visible) => {
  if (!visible) query.value = "";
});
</script>

<style scoped>
.cond-field-picker-trigger {
  width: 150px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 0 11px;
  border: 1px solid var(--fs-border);
  border-radius: var(--fs-radius-sm);
  background: var(--fs-bg-surface);
  color: var(--fs-text-primary);
  font-size: 13px;
  line-height: 1.4;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.cond-field-picker-trigger:hover {
  border-color: var(--fs-color-primary);
}

.cond-field-picker-trigger.placeholder .cond-field-picker-trigger-text {
  color: var(--fs-text-muted);
}

.cond-field-picker-trigger-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  text-align: left;
}

.cond-field-picker-trigger-icon {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--fs-text-muted);
}
</style>

<style>
.cond-field-picker-popover .ant-popover-inner {
  padding: 10px 12px 12px;
}

.cond-field-picker-search {
  margin-bottom: 4px;
}

.cond-field-picker-body {
  max-height: 420px;
  overflow-y: auto;
  padding-right: 2px;
}

.cond-field-picker-group{
  margin-top: 12px;
}

.cond-field-picker-group-title {
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: 0.02em;
  color: var(--fs-text-muted);
}

.cond-field-picker-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 4px;
}

.cond-field-picker-btn {
  padding: 5px 8px;
  border: 1px solid var(--fs-border);
  border-radius: var(--fs-radius-sm);
  background: var(--fs-bg-surface);
  color: var(--fs-text-primary);
  font-size: 12px;
  line-height: 1.35;
  text-align: left;
  cursor: pointer;
  transition: border-color .15s ease, background .15s ease, color .15s ease;
}

.cond-field-picker-btn:hover {
  border-color: var(--fs-color-primary);
  color: var(--fs-color-primary);
}

.cond-field-picker-btn.active {
  border-color: var(--fs-color-primary);
  background: color-mix(in srgb, var(--fs-color-primary) 10%, var(--fs-bg-surface));
  color: var(--fs-color-primary);
  font-weight: 600;
}

@media (max-width: 640px) {
  .cond-field-picker-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
