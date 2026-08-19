<template>
  <div class="fs-mobile-table">
    <a-spin :spinning="loading">
      <a-empty v-if="!dataSource.length" description="暂无数据" />
      <div v-for="row in dataSource" :key="String(row[rowKey])" class="mobile-card fs-card">
        <div class="mobile-card-head">
          <a-checkbox v-if="selectable" :checked="isSelected(row[rowKey])" class="mobile-card-check"
            @change="(e) => onSelect(row[rowKey], e.target.checked)" />
          <div class="mobile-card-head-main">
            <slot name="head" :record="row">
              <span class="mobile-card-title">{{ titleText(row) }}</span>
            </slot>
          </div>
          <div v-if="$slots.headExtra" class="mobile-card-head-extra">
            <slot name="headExtra" :record="row" />
          </div>
        </div>

        <div v-if="bodyColumns.length" class="mobile-card-body">
          <div v-for="col in bodyColumns" :key="columnKey(col)" class="mobile-field">
            <span class="mobile-field-label">{{ col.title }}</span>
            <span class="mobile-field-value">
              <slot name="cell" :column="col" :record="row" :text="cellText(row, col)">
                {{ cellText(row, col) }}
              </slot>
            </span>
          </div>
        </div>

        <div v-if="actionsColumn" class="mobile-card-actions">
          <slot name="cell" :column="actionsColumn" :record="row" :text="undefined" />
        </div>
      </div>

      <div v-if="showPagination" class="mobile-pagination">
        <a-pagination :current="pagination?.current || 1" :page-size="pagination?.pageSize || DEFAULT_PAGE_SIZE"
          :total="pagination?.total || 0" :size="pagination?.size || 'small'"
          :show-size-changer="pagination?.showSizeChanger"
          :page-size-options="pagination?.pageSizeOptions || DEFAULT_PAGE_SIZE_OPTIONS" :show-total="showTotal"
          @change="onPageChange" @show-size-change="onPageSizeChange" />
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { DEFAULT_PAGE_SIZE, DEFAULT_PAGE_SIZE_OPTIONS } from "@/composables/useResponsivePagination";

const props = withDefaults(
  defineProps<{
    columns: any[];
    dataSource: any[];
    loading?: boolean;
    pagination?: Record<string, any> | false | null;
    rowKey?: string;
    titleKey?: string;
    excludeKeys?: string[];
    selectable?: boolean;
    selectedKeys?: Array<string | number>;
  }>(),
  {
    rowKey: "id",
    excludeKeys: () => ["actions", "enabled"],
    selectable: false,
    selectedKeys: () => [],
  },
);

const emit = defineEmits<{
  change: [pagination: { current?: number; pageSize?: number }];
  select: [key: string | number, checked: boolean];
}>();

const actionsColumn = computed(() => props.columns.find((col) => col.key === "actions"));

const titleColumn = computed(() => {
  if (props.titleKey) {
    return (
      props.columns.find((col) => col.key === props.titleKey || col.dataIndex === props.titleKey) ||
      props.columns[0]
    );
  }
  return props.columns.find((col) => col.dataIndex) || props.columns[0];
});

const bodyColumns = computed(() =>
  props.columns.filter((col) => {
    if (col.key === "actions") return false;
    if (props.excludeKeys.includes(col.key)) return false;
    const title = titleColumn.value;
    if (title && columnKey(col) === columnKey(title)) return false;
    return true;
  }),
);

const showPagination = computed(() => {
  if (!props.pagination) return false;
  const total = Number(props.pagination.total || 0);
  const pageSize = Number(props.pagination.pageSize || DEFAULT_PAGE_SIZE);
  return total > pageSize;
});

function columnKey(col: any) {
  return String(col.key || col.dataIndex || col.title);
}

function cellText(row: Record<string, any>, col: any) {
  if (!col.dataIndex) return "";
  const value = row[col.dataIndex as string];
  if (value == null || value === "") return "—";
  return String(value);
}

function titleText(row: Record<string, any>) {
  const col = titleColumn.value;
  if (!col) return `#${row[props.rowKey]}`;
  const text = cellText(row, col);
  return text === "—" ? `#${row[props.rowKey]}` : text;
}

function isSelected(key: string | number) {
  return props.selectedKeys.map(String).includes(String(key));
}

function onSelect(key: string | number, checked: boolean) {
  emit("select", key, checked);
}

function onPageChange(page: number, pageSize: number) {
  emit("change", { current: page, pageSize });
}

function onPageSizeChange(_current: number, pageSize: number) {
  emit("change", { current: 1, pageSize });
}

function showTotal(total: number) {
  return `共 ${total} 条`;
}
</script>

<style scoped>
.fs-mobile-table {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-card {
  padding: 14px;
}

.mobile-card+.mobile-card {
  margin-top: 12px;
}

.mobile-card-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
}

.mobile-card-check {
  flex-shrink: 0;
}

.mobile-card-head-main {
  flex: 1;
  min-width: 0;
}

.mobile-card-head-extra {
  flex-shrink: 0;
}

.mobile-card-title {
  display: block;
  font-weight: 600;
  font-size: 15px;
  line-height: 1.4;
  color: var(--fs-text-primary);
  word-break: break-word;
}

.mobile-card-body {
  display: grid;
  gap: 10px;
}

.mobile-field {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 10px;
  align-items: baseline;
  font-size: 13px;
}

.mobile-field-label {
  color: var(--fs-text-muted);
}

.mobile-field-value {
  color: var(--fs-text-primary);
  word-break: break-word;
  line-height: 1.5;
  text-align: right;
}

.mobile-field-value .ant-tag{
  margin-inline-end: 0px;
  margin-inline-start: 6px;
}

.mobile-card-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--fs-border);
}

.mobile-card-more {
  margin-left: auto;
}

.mobile-card-actions :deep(.ant-divider-vertical) {
  display: none;
}

.mobile-card-actions :deep(a) {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 4px;
}

.mobile-pagination {
  display: flex;
  justify-content: center;
  padding: 8px 0 4px;
}
</style>
