<template>
  <page-shell title="自定义规则" description="按条件匹配请求并执行观察、拦截或人机验证等防护动作">
    <template #actions>
      <a-button type="primary" @click="crudRef?.openCreate()">新增规则</a-button>
    </template>
    <resource-crud ref="crudRef" embedded title="自定义规则" api-base="/api/v1/rules" :columns="columns" :filters="filters"
      :default-sort="defaultSort" :default-record="defaultRecord" :prepare-payload="preparePayload" :batch="batchConfig"
      name-field="name" detail-actions duplicatable>
      <template #cell="{ column, record }">
        <template v-if="column.key === 'mode'">
          <a-tag :color="modeColor[record.mode]">{{ modeLabel[record.mode] || record.mode }}</a-tag>
        </template>
        <site-ids-cell v-else-if="column.key === 'site_ids'" :site-ids="record.site_ids" />
      </template>
      <template #form="{ record, readonly, mode, enabledLoading, onEnabledPersist }">
        <fs-form-section title="规则信息">
          <template #extra>
            <form-enabled-switch v-model:checked="record.enabled" :immediate="mode === 'view'" :loading="enabledLoading"
              @immediate-change="onEnabledPersist" />
          </template>
          <a-form-item label="规则名称" required>
            <a-input v-model:value="record.name" :disabled="readonly" />
          </a-form-item>
          <a-form-item label="备注">
            <a-textarea v-model:value="record.remark" :disabled="readonly" placeholder="可选"
              :auto-size="{ minRows: 1, maxRows: 6 }" />
          </a-form-item>
          <a-row :gutter="16">
            <a-col :span="8">
              <a-form-item label="优先级 (小=先)">
                <a-input-number v-model:value="record.priority" :min="1" style="width: 100%" :disabled="readonly" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="生效站点">
                <site-select v-model:value="record.site_ids" style="width: 100%" :readonly="readonly" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="防护方式">
                <a-select v-model:value="record.mode" style="width: 100%" :disabled="readonly">
                  <a-select-option value="observe">观察模式</a-select-option>
                  <a-select-option value="block">拦截模式</a-select-option>
                  <a-select-option value="captcha">数学计算验证</a-select-option>
                  <a-select-option value="js_challenge">JS 挑战</a-select-option>
                  <a-select-option value="slide_captcha">滑动验证</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
        </fs-form-section>

        <fs-form-section title="匹配条件" description="配置请求匹配逻辑，支持嵌套条件组">
          <condition-editor v-model:value="record.conditions" :readonly="readonly" />
        </fs-form-section>

        <block-page-form-section v-if="record.mode === 'block'" :record="record" :readonly="readonly"
          switch-label="启用规则专属拦截页" description="关闭时使用站点或全局防护页面；命中本规则时优先使用此处配置" />
      </template>
    </resource-crud>
  </page-shell>
</template>

<script setup lang="ts">
import { ref } from "vue";
import BlockPageFormSection from "@/components/BlockPageFormSection.vue";
import ConditionEditor from "@/components/ConditionEditor.vue";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import PageShell from "@/components/PageShell.vue";
import ResourceCrud from "@/components/ResourceCrud.vue";
import SiteIdsCell from "@/components/SiteIdsCell.vue";
import SiteSelect from "@/components/SiteSelect.vue";
import { enabledFilterOptions, modeFilterOptions, siteScopeFilterField } from "@/constants/resourceList";
import { commonBatchEditFields } from "@/constants/batch";
import { siteIdsColumn } from "@/composables/useSiteOptions";
import { BLOCK_PAGE_FIELD_DEFAULTS, validateBlockPageOverride } from "@/constants/blockPage";
import { hasMatchingConditions } from "@/utils/conditions";
import type { BatchConfig } from "@/types/batch";
import type { ResourceColumn, ResourceDefaultSort, ResourceFilterField } from "@/types/resourceList";

const crudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);

const modeLabel: Record<string, string> = {
  observe: "观察",
  block: "拦截",
  captcha: "数学计算验证",
  js_challenge: "JS挑战",
  slide_captcha: "滑动验证",
};
const modeColor: Record<string, string> = {
  observe: "blue",
  block: "red",
  captcha: "orange",
  js_challenge: "purple",
  slide_captcha: "cyan",
};

const filters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "规则名称 / 备注" },
  { key: "mode", label: "动作", type: "select", width: "200px", options: modeFilterOptions },
  { key: "enabled", label: "状态", type: "select", width: "140px", options: enabledFilterOptions },
  siteScopeFilterField,
];

const defaultSort: ResourceDefaultSort = { field: "priority", order: "asc" };

const batchConfig: BatchConfig = {
  modeOptions: modeFilterOptions,
  editFields: [
    commonBatchEditFields.enabled,
    commonBatchEditFields.mode,
    commonBatchEditFields.priority,
    commonBatchEditFields.siteIds,
  ],
};

const columns: ResourceColumn[] = [
  { title: "名称", dataIndex: "name", width: 360, ellipsis: true, sorter: true },
  { title: "备注", dataIndex: "remark", minWidth: 200, ellipsis: true },
  { title: "优先级", dataIndex: "priority", width: 90, sorter: true },
  { title: "模式", key: "mode", dataIndex: "mode", width: 110, slotCell: true, sorter: true },
  siteIdsColumn(),
  { title: "状态", key: "enabled", dataIndex: "enabled", width: 90, sorter: true },
];

const defaultRecord = () => ({
  name: "",
  remark: "",
  mode: "block",
  priority: 100,
  site_ids: [],
  enabled: true,
  conditions: { logic: "and", conditions: [] },
  ...BLOCK_PAGE_FIELD_DEFAULTS,
});

function preparePayload(row: Record<string, any>) {
  if (row.mode !== "observe" && !hasMatchingConditions(row.conditions)) {
    throw new Error("非观察模式必须配置至少一条匹配条件");
  }
  if (row.mode !== "block") {
    row.custom_block_page_enabled = false;
  }
  validateBlockPageOverride(row);
  return row;
}
</script>
