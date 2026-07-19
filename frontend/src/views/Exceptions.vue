<template>
  <page-shell title="防护例外" description="为特定流量跳过全部或部分防护检测">
    <template #actions>
      <a-button type="primary" @click="crudRef?.openCreate()">新增</a-button>
    </template>
    <resource-crud
    ref="crudRef"
    embedded
    title="防护例外"
    api-base="/api/v1/exceptions"
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
      <template v-if="column.key === 'scope'">
        <a-tag>{{ scopeLabel[record.scope] || record.scope }}</a-tag>
      </template>
      <site-ids-cell v-else-if="column.key === 'site_ids'" :site-ids="record.site_ids" />
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
        <a-row :gutter="16">
          <a-col :xs="24" :sm="10" :md="8">
            <a-form-item label="跳过范围">
              <a-select v-model:value="record.scope" style="width: 100%" :disabled="readonly">
                <a-select-option value="all">跳过全部防护</a-select-option>
                <a-select-option value="rules">跳过自定义规则</a-select-option>
                <a-select-option value="ratelimit">跳过限速限制</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="14" :md="16">
            <a-form-item label="生效站点（不选=全局）">
              <site-select v-model:value="record.site_ids" :readonly="readonly" class="site-select-block" />
            </a-form-item>
          </a-col>
        </a-row>
      </fs-form-section>
      <fs-form-section title="命中条件" :description="conditionHint(record.scope)">
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
import {
  enabledFilterOptions,
  exceptionScopeFilterOptions,
  siteScopeFilterField,
} from "@/constants/resourceList";
import { commonBatchEditFields } from "@/constants/batch";
import { siteIdsColumn } from "@/composables/useSiteOptions";
import { hasMatchingConditions } from "@/utils/conditions";
import type { BatchConfig } from "@/types/batch";
import type { ResourceColumn, ResourceFilterField } from "@/types/resourceList";

const crudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);

const scopeLabel: Record<string, string> = {
  all: "全部防护",
  rules: "仅规则",
  ratelimit: "仅限速",
};

const listFilters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "名称" },
  { key: "scope", label: "范围", type: "select", options: exceptionScopeFilterOptions },
  { key: "enabled", label: "状态", type: "select", options: enabledFilterOptions },
  siteScopeFilterField,
];

const batchConfig: BatchConfig = {
  editFields: [
    commonBatchEditFields.enabled,
    commonBatchEditFields.scope,
    commonBatchEditFields.siteIds,
  ],
};

const columns: ResourceColumn[] = [
  { title: "名称", dataIndex: "name", sorter: true },
  { title: "范围", key: "scope", dataIndex: "scope", width: 120, slotCell: true, sorter: true },
  siteIdsColumn(),
  { title: "状态", key: "enabled", dataIndex: "enabled", width: 90, sorter: true },
];

const defaultRecord = () => ({
  name: "",
  scope: "rules",
  site_ids: [],
  enabled: true,
  conditions: { logic: "and", conditions: [] },
});

function conditionHint(scope: string) {
  if (scope === "all") {
    return "跳过全部防护时必须至少配置一条匹配条件";
  }
  return "命中即按范围跳过防护；不配置条件则对所有请求生效";
}

function preparePayload(row: Record<string, any>) {
  if (row.scope === "all" && !hasMatchingConditions(row.conditions)) {
    throw new Error("跳过全部防护时必须配置至少一条匹配条件");
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
