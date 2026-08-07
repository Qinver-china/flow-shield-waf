<template>
  <div class="resource-crud">
    <div v-if="!embedded" class="toolbar">
      <h3>{{ title }}</h3>
      <a-button v-if="showCreate" type="primary" @click="openCreate">{{ createLabel }}</a-button>
    </div>

    <list-filter-bar
      v-if="filters?.length"
      :fields="filters"
      :model="filterValues"
      @change="onFilterChange"
      @reset="resetFilters"
    />

    <slot
      v-if="$slots.list"
      name="list"
      :rows="rows"
      :loading="loading"
      :open-view="openView"
      :open-edit="openEdit"
      :open-duplicate="openDuplicate"
      :remove="remove"
      :toggle-enabled="toggleEnabled"
      :toggling-id="togglingId"
      :allow-delete="allowDelete"
      :name-actions="nameActions"
      :duplicatable="duplicatable"
      :pagination="pagination"
      :on-table-change="onTableChange"
    />

    <a-table
      v-else-if="!isMobile"
      :columns="tableColumns"
      :data-source="rows"
      :loading="loading"
      :pagination="pagination"
      :row-selection="rowSelection"
      row-key="id"
      size="middle"
      bordered
      :scroll="{ x: tableScrollX }"
      :show-sorter-tooltip="false"
      @change="onTableChange"
    >
      <template #bodyCell="{ column, record, text }">
        <template v-if="column.key === '__actions'">
          <a @click="openView(record)">查看</a>
          <a-divider type="vertical" />
          <a @click="openEdit(record)">编辑</a>
          <template v-if="duplicatable">
            <a-divider type="vertical" />
            <a @click="openDuplicate(record)">复制</a>
          </template>
          <template v-if="allowDelete(record)">
            <a-divider type="vertical" />
            <a-popconfirm title="确认删除?" @confirm="remove(record.id)">
              <a class="danger">删除</a>
            </a-popconfirm>
          </template>
        </template>
        <template v-else-if="nameField && column.dataIndex === nameField">
          <resource-name-cell
            :text="String(text ?? '')"
            :actions="nameActions(record)"
            @view="openView(record)"
          />
        </template>
        <template v-else-if="column.key === 'enabled'">
          <a-switch
            :checked="record.enabled"
            :loading="togglingId === record.id"
            @change="(checked: boolean) => toggleEnabled(record, checked)"
          />
        </template>
        <template v-else-if="column.slotCell">
          <slot name="cell" :column="column" :record="record" />
        </template>
        <template v-else>
          {{ column.customRender ? column.customRender({ text, record }) : text }}
        </template>
      </template>
    </a-table>

    <div v-else class="mobile-list">
      <a-spin :spinning="loading">
        <a-empty v-if="!rows.length" description="暂无数据" />
        <div v-for="row in rows" :key="row.id" class="mobile-card fs-card">
          <div class="mobile-card-head">
            <div class="mobile-card-head-left">
              <a-checkbox
                v-if="batchEnabled"
                :checked="isMobileRowSelected(row.id)"
                class="mobile-card-check"
                @change="(e: any) => toggleMobileRow(row.id, e.target.checked)"
              />
              <a class="mobile-card-title" @click="openView(row)">
                {{ nameField ? row[nameField] : `#${row.id}` }}
              </a>
            </div>
            <a-switch
              v-if="hasEnabledColumn"
              :checked="row.enabled"
              :loading="togglingId === row.id"
              @change="(checked: boolean) => toggleEnabled(row, checked)"
            />
          </div>
          <div class="mobile-card-body">
            <div
              v-for="col in displayColumns"
              :key="col.key || col.dataIndex"
              class="mobile-field"
            >
              <span class="mobile-field-label">{{ col.title }}</span>
              <span class="mobile-field-value">
                <template v-if="col.slotCell">
                  <slot name="cell" :column="col" :record="row" />
                </template>
                <template v-else>
                  {{ col.customRender ? col.customRender({ text: row[col.dataIndex as string], record: row }) : row[col.dataIndex as string] }}
                </template>
              </span>
            </div>
          </div>
          <div class="mobile-card-actions">
            <a-button size="small" @click="openView(row)">查看</a-button>
            <a-button size="small" type="primary" ghost @click="openEdit(row)">编辑</a-button>
            <a-dropdown v-if="mobileMoreActions(row).length" class="mobile-card-more" :arrow="true">
              <a-button size="small">更多</a-button>
              <template #overlay>
                <a-menu :selectable="false">
                  <template v-for="(action, index) in mobileMoreActions(row)" :key="action.key">
                    <a-menu-divider v-if="action.divided && index > 0" />
                    <a-menu-item :danger="action.danger" @click="() => runAction(action)">
                      {{ action.label }}
                    </a-menu-item>
                  </template>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
        </div>
        <div v-if="total > pageSize" class="mobile-pagination">
          <a-pagination
            v-model:current="page"
            :total="total"
            :page-size="pageSize"
            :size="paginationSize"
            :show-total="(t: number) => `共 ${t} 条`"
            :show-size-changer="total > DEFAULT_PAGE_SIZE"
            :page-size-options="DEFAULT_PAGE_SIZE_OPTIONS"
            @change="onMobilePageChange"
          />
        </div>
      </a-spin>
    </div>

    <fs-form-drawer
      v-model:open="drawerOpen"
      :title="drawerTitle"
      :subtitle="drawerSubtitle"
      :mode="drawerMode"
      :confirm-loading="saving"
      :json-content="drawerMode === 'view' && props.showViewJson ? recordJson : undefined"
      @ok="save"
    >
      <a-form layout="vertical">
        <a-tabs
          v-if="showJsonImport"
          v-model:active-key="createFormTab"
          class="resource-crud__create-tabs"
        >
          <a-tab-pane key="form" tab="表单填写">
            <slot
              name="form"
              :record="record"
              :readonly="false"
              :mode="drawerMode"
              :enabled-loading="drawerEnabledToggling"
              :on-enabled-persist="persistDrawerEnabled"
            />
          </a-tab-pane>
          <a-tab-pane key="import" tab="JSON 导入">
            <resource-json-import
              :default-record="defaultRecord"
              bare
              @import="onJsonImport"
            />
          </a-tab-pane>
        </a-tabs>
        <slot
          v-else
          name="form"
          :record="record"
          :readonly="drawerMode === 'view'"
          :mode="drawerMode"
          :enabled-loading="drawerEnabledToggling"
          :on-enabled-persist="persistDrawerEnabled"
        />
      </a-form>
      <template v-if="drawerMode === 'view' && detailActions" #view-actions>
        <a-button type="primary" @click="switchToEdit">编辑</a-button>
        <a-button v-if="duplicatable" @click="switchToDuplicate">复制</a-button>
        <a-popconfirm v-if="allowDelete(record)" title="确认删除?" @confirm="deleteCurrent">
          <a-button danger>删除</a-button>
        </a-popconfirm>
      </template>
    </fs-form-drawer>

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
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Modal, message } from "ant-design-vue";
import { api } from "@/api";
import ListFilterBar from "@/components/ListFilterBar.vue";
import ResourceNameCell from "@/components/ResourceNameCell.vue";
import FsFormDrawer, { type FormDrawerMode } from "@/components/FsFormDrawer.vue";
import ResourceJsonImport from "@/components/ResourceJsonImport.vue";
import TableBatchBar from "@/components/TableBatchBar.vue";
import BatchEditDrawer from "@/components/BatchEditDrawer.vue";
import { useResponsivePagination } from "@/composables/useResponsivePagination";
import { useResourceQuickActions } from "@/composables/useResourceQuickActions";
import { useTableBatch } from "@/composables/useTableBatch";
import type { BatchConfig } from "@/types/batch";
import type {
  ResourceColumn,
  ResourceDefaultSort,
  ResourceFilterField,
} from "@/types/resourceList";

const props = withDefaults(
  defineProps<{
    title: string;
    apiBase: string;
    columns: ResourceColumn[];
    defaultRecord: () => Record<string, any>;
    filters?: ResourceFilterField[];
    defaultSort?: ResourceDefaultSort;
    duplicatable?: boolean;
    duplicateRecord?: (row: Record<string, any>) => Record<string, any>;
    nameField?: string;
    detailActions?: boolean;
    embedded?: boolean;
    batch?: BatchConfig | false;
    createLabel?: string;
    showCreate?: boolean;
    showViewJson?: boolean;
    mapRecord?: (row: Record<string, any>) => Record<string, any>;
    preparePayload?: (
      row: Record<string, any>,
      mode: FormDrawerMode,
    ) => Record<string, any> | Promise<Record<string, any>>;
    canDelete?: (row: Record<string, any>) => boolean;
  }>(),
  { duplicatable: false, detailActions: false, embedded: false, showViewJson: true, createLabel: "新增", showCreate: true },
);

const emit = defineEmits<{
  mutated: [];
}>();

function notifyMutated() {
  emit("mutated");
}

function allowDelete(row: Record<string, any>) {
  return props.canDelete ? props.canDelete(row) : true;
}

const { isMobile, paginationSize, withPaginationSize, DEFAULT_PAGE_SIZE, DEFAULT_PAGE_SIZE_OPTIONS } =
  useResponsivePagination();
const route = useRoute();
const router = useRouter();
const { buildActions, runAction } = useResourceQuickActions();

const rows = ref<any[]>([]);
const loading = ref(false);
let fetchSeq = 0;
const saving = ref(false);
const drawerOpen = ref(false);
const drawerMode = ref<FormDrawerMode>("create");
const record = reactive<Record<string, any>>({});
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const togglingId = ref<number | null>(null);
const drawerEnabledToggling = ref(false);
const createFormTab = ref<"form" | "import">("form");
const filterValues = reactive<Record<string, unknown>>({});
const sortField = ref(props.defaultSort?.field);
const sortOrder = ref<"asc" | "desc" | undefined>(props.defaultSort?.order);

const tableScrollX = computed(() => (props.columns.length > 4 ? 900 : undefined));

const drawerTitle = computed(() => props.title);

const drawerSubtitle = computed(() => {
  const name = props.nameField ? record[props.nameField] : "";
  if (drawerMode.value === "copy") return name ? `${name} · 副本` : "副本";
  if (drawerMode.value === "view" && name) return String(name);
  if (record.id) return name ? `${name} · #${record.id}` : `#${record.id}`;
  return undefined;
});

const recordJson = computed(() => JSON.stringify(record, null, 2));

const showJsonImport = computed(
  () => drawerMode.value === "create" || drawerMode.value === "copy",
);

const hasEnabledColumn = computed(() => props.columns.some((c) => c.key === "enabled"));

const batchConfig = computed<BatchConfig | undefined>(() =>
  props.batch === false ? undefined : props.batch,
);

const displayColumns = computed(() =>
  props.columns.filter((c) => c.key !== "__actions" && c.key !== "enabled" && c.dataIndex !== props.nameField),
);

function columnSortKey(column: ResourceColumn) {
  return column.sortKey || column.dataIndex || column.key;
}

const tableColumns = computed(() => {
  const cols = props.columns.map((column) => {
    if (!column.sorter) return column;
    const key = columnSortKey(column);
    return {
      ...column,
      sorter: true,
      sortOrder:
        sortField.value === key
          ? sortOrder.value === "asc"
            ? "ascend"
            : "descend"
          : undefined,
    };
  });
  if (!props.detailActions) {
    cols.push({
      title: "操作",
      key: "__actions",
      width: props.duplicatable ? 220 : 180,
    });
  }
  return cols;
});

const pagination = computed(() =>
  withPaginationSize({
    current: page.value,
    pageSize: pageSize.value,
    total: total.value,
    showTotal: (t: number) => `共 ${t} 条`,
  }),
);

function buildQueryParams() {
  const params: Record<string, unknown> = {
    page: page.value,
    page_size: pageSize.value,
  };
  if (sortField.value && sortOrder.value) {
    params.sort_by = sortField.value;
    params.sort_order = sortOrder.value;
  }
  for (const field of props.filters ?? []) {
    const value = filterValues[field.key];
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      if (value.length > 0) params[field.key] = value;
      continue;
    }
    params[field.key] = value;
  }
  return params;
}

async function fetchList() {
  const seq = ++fetchSeq;
  loading.value = true;
  try {
    const resp = await api.get(props.apiBase, buildQueryParams());
    if (seq !== fetchSeq) return;
    rows.value = resp.data.items;
    total.value = resp.data.total;
  } finally {
    if (seq === fetchSeq) {
      loading.value = false;
    }
  }
}

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
  toggleMobileRow,
  isMobileRowSelected,
  batchEnable,
  batchSwitchMode,
  batchDelete,
  batchUpdate,
  availableActions,
} = useTableBatch({
  apiBase: props.apiBase,
  rows,
  batch: batchConfig,
  hasEnabledColumn,
  onRefresh: async () => {
    await fetchList();
    notifyMutated();
  },
});

function onBatchExecute(action: import("@/types/batch").BatchActionKey, mode?: string) {
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

function onTableChange(pg: any, _filters: any, sorter: any) {
  page.value = pg.current;
  pageSize.value = pg.pageSize;
  const active = Array.isArray(sorter) ? sorter.find((item) => item.order) : sorter;
  if (active?.order) {
    sortField.value = active.field || active.columnKey;
    sortOrder.value = active.order === "ascend" ? "asc" : "desc";
  } else {
    sortField.value = props.defaultSort?.field;
    sortOrder.value = props.defaultSort?.order;
  }
  fetchList();
}

function onMobilePageChange(p: number, size?: number) {
  page.value = p;
  if (size) pageSize.value = size;
  fetchList();
}

function onFilterChange() {
  page.value = 1;
  if (selectedCount.value > 0) {
    Modal.confirm({
      title: "筛选条件已变更",
      content: `当前仍选中 ${selectedCount.value} 项（可能含跨页选择）。是否清空选择后再刷新列表？`,
      okText: "清空并刷新",
      cancelText: "保留选择",
      onOk: () => {
        clearSelection();
        fetchList();
      },
      onCancel: () => {
        fetchList();
      },
    });
    return;
  }
  fetchList();
}

function resetFilters() {
  for (const field of props.filters ?? []) {
    filterValues[field.key] = undefined;
  }
  page.value = 1;
  fetchList();
}

function reset(obj: Record<string, any>) {
  Object.keys(record).forEach((k) => delete record[k]);
  Object.assign(record, obj);
}

function onJsonImport(merged: Record<string, unknown>) {
  reset(applyMapRecord(merged));
  createFormTab.value = "form";
}

function applyMapRecord(row: Record<string, any>) {
  return props.mapRecord ? props.mapRecord(row) : row;
}

function openCreate() {
  drawerMode.value = "create";
  createFormTab.value = "form";
  reset(applyMapRecord(props.defaultRecord()));
  drawerOpen.value = true;
}

function openEdit(row: any) {
  drawerMode.value = "edit";
  reset(applyMapRecord(JSON.parse(JSON.stringify(row))));
  drawerOpen.value = true;
}

function buildDuplicate(row: Record<string, any>) {
  if (props.duplicateRecord) {
    return props.duplicateRecord(JSON.parse(JSON.stringify(row)));
  }
  const copy = JSON.parse(JSON.stringify(row));
  delete copy.id;
  if (typeof copy.name === "string" && copy.name.trim()) {
    const suffix = " (副本)";
    copy.name = copy.name.endsWith(suffix) ? copy.name : `${copy.name}${suffix}`;
  }
  return copy;
}

function openDuplicate(row: any) {
  drawerMode.value = "copy";
  createFormTab.value = "form";
  reset(applyMapRecord(buildDuplicate(row)));
  drawerOpen.value = true;
}

function openView(row: any) {
  drawerMode.value = "view";
  reset(applyMapRecord(JSON.parse(JSON.stringify(row))));
  drawerOpen.value = true;
}

async function openDrawerById(id: number, mode: "view" | "edit") {
  try {
    const resp = await api.get(`${props.apiBase}/${id}`);
    if (mode === "edit") openEdit(resp.data);
    else openView(resp.data);
  } catch {
    message.error("加载资源失败");
  }
}

function parseRouteDrawerQuery() {
  const rawId = route.query.id;
  const rawDrawer = route.query.drawer;
  if (!rawId || !rawDrawer) return null;
  const drawer = Array.isArray(rawDrawer) ? rawDrawer[0] : rawDrawer;
  if (drawer !== "view" && drawer !== "edit") return null;
  const id = Number(Array.isArray(rawId) ? rawId[0] : rawId);
  if (!Number.isFinite(id)) return null;
  return { id, mode: drawer as "view" | "edit" };
}

function syncRouteDrawer() {
  const parsed = parseRouteDrawerQuery();
  if (!parsed) return;
  void openDrawerById(parsed.id, parsed.mode);
}

function clearRouteDrawerQuery() {
  if (!route.query.id && !route.query.drawer) return;
  const nextQuery = { ...route.query };
  delete nextQuery.id;
  delete nextQuery.drawer;
  router.replace({ query: nextQuery });
}

function nameActions(row: Record<string, any>) {
  return buildActions(
    props.apiBase,
    row,
    {
      openEdit: () => openEdit(row),
      openDuplicate: props.duplicatable ? () => openDuplicate(row) : undefined,
      remove: allowDelete(row) ? () => remove(row.id) : undefined,
    },
    { duplicatable: props.duplicatable },
  );
}

function mobileMoreActions(row: Record<string, any>) {
  return nameActions(row).filter((action) => action.key !== "edit");
}

function switchToEdit() {
  drawerMode.value = "edit";
}

function switchToDuplicate() {
  drawerMode.value = "copy";
  createFormTab.value = "form";
  reset(applyMapRecord(buildDuplicate(record)));
}

async function deleteCurrent() {
  const id = record.id;
  if (!id) return;
  drawerOpen.value = false;
  await remove(id);
}

async function save() {
  saving.value = true;
  try {
    const payload = props.preparePayload
      ? await Promise.resolve(props.preparePayload({ ...record }, drawerMode.value))
      : record;
    const resp =
      record.id && drawerMode.value === "edit"
        ? await api.put(`${props.apiBase}/${record.id}`, payload)
        : await api.post(props.apiBase, payload);
    const tip = resp?.message && resp.message !== "ok" ? resp.message : "保存成功";
    if (resp?.message && resp.message !== "ok") message.warning(tip);
    else message.success(tip);
    drawerOpen.value = false;
    fetchList();
    notifyMutated();
  } catch (err: any) {
    if (err?.message === "cancelled") {
      // user dismissed confirm; keep drawer open
    } else if (!err?.response && err?.message) {
      message.error(err.message);
    }
  } finally {
    saving.value = false;
  }
}

async function remove(id: number) {
  await api.del(`${props.apiBase}/${id}`);
  message.success("已删除");
  fetchList();
  notifyMutated();
}

async function toggleEnabled(row: any, enabled: boolean) {
  togglingId.value = row.id;
  try {
    await api.put(`${props.apiBase}/${row.id}`, { enabled });
    row.enabled = enabled;
    message.success(enabled ? "已启用" : "已停用");
    notifyMutated();
  } catch {
    // interceptor shows error; keep previous switch state
  } finally {
    togglingId.value = null;
  }
}

async function persistDrawerEnabled(enabled: boolean) {
  if (drawerMode.value !== "view" || !record.id) return;
  const previous = record.enabled;
  drawerEnabledToggling.value = true;
  try {
    await api.put(`${props.apiBase}/${record.id}`, { enabled });
    record.enabled = enabled;
    const row = rows.value.find((item) => item.id === record.id);
    if (row) row.enabled = enabled;
    message.success(enabled ? "已启用" : "已停用");
    notifyMutated();
  } catch {
    record.enabled = previous;
  } finally {
    drawerEnabledToggling.value = false;
  }
}

defineExpose({
  fetchList,
  openCreate,
  openViewById: (id: number) => openDrawerById(id, "view"),
  openEditById: (id: number) => openDrawerById(id, "edit"),
});
function parseSiteFilterValue(raw: string | string[], multiple?: boolean) {
  const values = Array.isArray(raw) ? raw : [raw];
  const ids = values
    .flatMap((item) => String(item).split(","))
    .map((item) => Number(item.trim()))
    .filter((id) => Number.isFinite(id));
  if (!ids.length) return undefined;
  return multiple ? ids : ids[0];
}

function applyRouteFilters() {
  for (const field of props.filters ?? []) {
    const raw = route.query[field.key];
    if (raw === undefined || raw === null || raw === "") continue;
    if (field.type === "site") {
      const parsed = parseSiteFilterValue(
        Array.isArray(raw) ? raw.map(String) : String(raw),
        field.multiple,
      );
      if (parsed !== undefined) filterValues[field.key] = parsed;
      continue;
    }
    if (field.multiple) {
      const values = (Array.isArray(raw) ? raw : String(raw).split(","))
        .map((item) => String(item).trim())
        .filter(Boolean);
      if (values.length) filterValues[field.key] = values;
      continue;
    }
    const value = Array.isArray(raw) ? raw[0] : raw;
    if (field.key === "enabled") {
      filterValues[field.key] = value === "true" ? true : value === "false" ? false : value;
      continue;
    }
    filterValues[field.key] = value;
  }
}

onMounted(() => {
  applyRouteFilters();
  fetchList();
  syncRouteDrawer();
});

watch(drawerOpen, (open) => {
  if (!open) clearRouteDrawerQuery();
});

watch(
  () => [route.query.id, route.query.drawer],
  () => {
    if (route.query.id && route.query.drawer) syncRouteDrawer();
  },
);
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
}

.toolbar h3 {
  margin: 0;
  font-size: 18px;
  color: var(--fs-text-primary);
}

.danger {
  color: var(--fs-color-danger);
}

.name-link {
  color: var(--fs-color-primary);
  cursor: pointer;
}

.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-card {
  padding: 14px;
  margin-bottom: 12px;
}

.mobile-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.mobile-card-check {
  flex-shrink: 0;
}

.mobile-card-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--fs-color-primary);
  margin-left: 10px;
}

.mobile-card-body {
  display: grid;
  gap: 8px;
}

.mobile-field {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.mobile-field-label {
  color: var(--fs-text-muted);
  flex-shrink: 0;
}

.mobile-field-value {
  text-align: right;
  color: var(--fs-text-primary);
  word-break: break-all;
}

.mobile-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--fs-border);
}

.mobile-card-more {
  margin-left: auto;
}

.mobile-pagination {
  display: flex;
  justify-content: center;
  padding: 8px 0;
}

.resource-crud__create-tabs {
  margin-top: -4px;
}
</style>
