<template>
  <page-shell title="全局白名单" description="命中白名单的请求将跳过后续防护检测">
    <template #actions>
      <a-button type="primary" @click="crudRef?.openCreate()">新增</a-button>
    </template>
    <resource-crud
    ref="crudRef"
    embedded
    title="全局白名单"
    api-base="/api/v1/whitelist"
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
        <a-form-item label="备注">
          <a-textarea
            v-model:value="record.remark"
            :disabled="readonly"
            placeholder="可选"
            :auto-size="{ minRows: 1, maxRows: 6 }"
          />
        </a-form-item>
        <a-form-item label="生效站点">
          <site-select v-model:value="record.site_ids" :readonly="readonly" class="site-select-block" />
        </a-form-item>
      </fs-form-section>
      <fs-form-section title="命中条件" description="不配置条件将放行全部流量，请谨慎使用">
        <condition-editor v-model:value="record.conditions" :readonly="readonly" />
      </fs-form-section>
    </template>
  </resource-crud>
  </page-shell>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Modal } from "ant-design-vue";
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
import { hasMatchingConditions } from "@/utils/conditions";
import type { BatchConfig } from "@/types/batch";
import type { ResourceColumn, ResourceFilterField } from "@/types/resourceList";

const crudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);

const listFilters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "名称 / 备注" },
  { key: "enabled", label: "状态", type: "select", options: enabledFilterOptions },
  siteScopeFilterField,
];

const batchConfig: BatchConfig = {
  editFields: [commonBatchEditFields.enabled, commonBatchEditFields.siteIds],
};

const columns: ResourceColumn[] = [
  { title: "名称", dataIndex: "name", width: 400, ellipsis: true, sorter: true },
  { title: "备注", dataIndex: "remark", ellipsis: true },
  siteIdsColumn(),
  { title: "状态", key: "enabled", dataIndex: "enabled", width: 90, sorter: true },
];

const defaultRecord = () => ({
  name: "",
  remark: "",
  site_ids: [],
  enabled: true,
  conditions: { logic: "and", conditions: [] },
});

function preparePayload(row: Record<string, any>) {
  if (row.enabled && !hasMatchingConditions(row.conditions)) {
    return new Promise<Record<string, any>>((resolve, reject) => {
      Modal.confirm({
        title: "确认启用空条件白名单？",
        content: "未配置命中条件时，启用后将放行全部流量并跳过后续防护。确定继续保存吗？",
        okText: "确认保存",
        okType: "danger",
        cancelText: "取消",
        onOk: () => resolve(row),
        onCancel: () => reject(new Error("cancelled")),
      });
    });
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
