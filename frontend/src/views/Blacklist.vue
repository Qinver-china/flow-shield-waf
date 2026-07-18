<template>
  <page-shell title="全局黑名单" description="命中黑名单的请求将被直接拦截">
    <template #actions>
      <a-button type="primary" @click="crudRef?.openCreate()">新增</a-button>
    </template>
    <resource-crud
    ref="crudRef"
    embedded
    title="全局黑名单"
    api-base="/api/v1/blacklist"
    :columns="columns"
    :filters="listFilters"
    :default-record="defaultRecord"
    :prepare-payload="preparePayload"
    :batch="batchConfig"
    name-field="name"
    detail-actions
    duplicatable
  >
    <template #cell="{ column, record }">
      <site-ids-cell v-if="column.key === 'site_ids'" :site-ids="record.site_ids" />
    </template>
    <template #form="{ record, readonly, mode, enabledLoading, onEnabledPersist }">
      <fs-form-section title="基本信息">
        <template #extra>
          <form-enabled-switch
            v-model:checked="record.enabled"
            :immediate="mode === 'view'"
            :loading="enabledLoading"
            @immediate-change="onEnabledPersist"
          />
        </template>
        <a-form-item label="名称" required>
          <a-input v-model:value="record.name" :disabled="readonly" />
        </a-form-item>
        <a-form-item label="生效站点（不选=全局）">
          <site-select v-model:value="record.site_ids" :readonly="readonly" class="site-select-block" />
        </a-form-item>
      </fs-form-section>
      <fs-form-section title="命中条件" description="命中即拦截；必须至少配置一条条件，否则会拦截全部流量">
        <condition-editor v-model:value="record.conditions" :readonly="readonly" />
      </fs-form-section>
    </template>
  </resource-crud>
  </page-shell>
</template>

<script setup lang="ts">
import { ref } from "vue";
import ConditionEditor from "@/components/ConditionEditor.vue";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import PageShell from "@/components/PageShell.vue";
import ResourceCrud from "@/components/ResourceCrud.vue";
import SiteIdsCell from "@/components/SiteIdsCell.vue";
import SiteSelect from "@/components/SiteSelect.vue";
import { enabledFilterOptions, siteScopeFilterField } from "@/constants/resourceList";
import { commonBatchEditFields } from "@/constants/batch";
import { siteIdsColumn } from "@/composables/useSiteOptions";
import type { BatchConfig } from "@/types/batch";
import type { ResourceColumn, ResourceFilterField } from "@/types/resourceList";

const crudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);

const listFilters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "名称" },
  { key: "enabled", label: "状态", type: "select", options: enabledFilterOptions },
  siteScopeFilterField,
];

const batchConfig: BatchConfig = {
  editFields: [commonBatchEditFields.enabled, commonBatchEditFields.siteIds],
};

const columns: ResourceColumn[] = [
  { title: "名称", dataIndex: "name", sorter: true },
  siteIdsColumn(),
  { title: "状态", key: "enabled", dataIndex: "enabled", width: 90, sorter: true },
];

const defaultRecord = () => ({
  name: "",
  site_ids: [],
  enabled: true,
  conditions: { logic: "and", conditions: [] },
});

function hasConditions(record: Record<string, any>) {
  return Array.isArray(record.conditions?.conditions) && record.conditions.conditions.length > 0;
}

function preparePayload(row: Record<string, any>) {
  if (!hasConditions(row)) {
    throw new Error("黑名单必须配置至少一条匹配条件");
  }
  return row;
}
</script>

<style scoped>
.site-select-block :deep(.ant-select) {
  width: 100%;
  min-width: 0;
}
</style>
