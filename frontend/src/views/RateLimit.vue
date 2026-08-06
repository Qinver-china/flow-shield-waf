<template>
  <page-shell title="自定义速率防护" description="按时间窗口与阈值限制请求频率，防范 CC 攻击">
    <template #actions>
      <a-button type="primary" @click="crudRef?.openCreate()">新增</a-button>
    </template>
    <resource-crud
    ref="crudRef"
    embedded
    title="自定义速率防护"
    api-base="/api/v1/ratelimit"
    :columns="columns"
    :filters="listFilters"
    :default-sort="defaultSort"
    :default-record="defaultRecord"
    :prepare-payload="preparePayload"
    :batch="batchConfig"
    name-field="name"
    detail-actions
    duplicatable
  >
    <template #cell="{ column, record }">
      <template v-if="column.key === 'mode'">
        <a-tag :color="modeColor[record.mode]">{{ modeLabel[record.mode] || record.mode }}</a-tag>
      </template>
      <site-ids-cell v-else-if="column.key === 'site_ids'" :site-ids="record.site_ids" />
    </template>
    <template #form="{ record, readonly, mode, enabledLoading, onEnabledPersist }">
      <fs-form-section title="策略配置">
        <template #extra>
          <form-enabled-switch
            v-model:checked="record.enabled"
            :immediate="mode === 'view'"
            :loading="enabledLoading"
            @immediate-change="onEnabledPersist"
          />
        </template>
        <a-form-item label="策略名称" required>
          <a-input v-model:value="record.name" :disabled="readonly" />
        </a-form-item>
        <a-form-item label="备注">
          <a-input v-model:value="record.remark" :disabled="readonly" placeholder="可选" />
        </a-form-item>
        <a-row :gutter="16" style="margin-bottom: 12px;">
          <a-col :xs="24" :sm="16" :md="18">
            <a-form-item label="生效站点（不选=全局）">
              <site-select v-model:value="record.site_ids" style="width: 100%" :readonly="readonly" class="site-select-block" />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="8" :md="6">
            <a-form-item label="优先级 (小=先)">
              <a-input-number v-model:value="record.priority" :min="1" style="width: 100%" :disabled="readonly" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16" style="margin-bottom: 12px;">
          <a-col :xs="12" :sm="8" :md="8">
            <a-form-item label="时间窗口 (秒)">
              <a-input-number
                v-model:value="record.window"
                :min="1"
                :disabled="readonly"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :xs="12" :sm="8" :md="8">
            <a-form-item label="阈值 (次)">
              <a-input-number
                v-model:value="record.threshold"
                :min="1"
                :disabled="readonly"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :sm="8" :md="8">
            <a-form-item label="超限动作">
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

      <fs-form-section title="限速维度" description="按 key 组合统计请求频率">
        <div v-for="(k, idx) in record.keys" :key="idx" class="key-row">
          <a-select
            v-model:value="k.field"
            class="key-field-select"
            placeholder="字段"
            :disabled="readonly"
          >
            <a-select-option v-for="f in keyFields" :key="f.value" :value="f.value">
              {{ f.label }}
            </a-select-option>
          </a-select>
          <a-input
            v-if="argFields.includes(k.field)"
            v-model:value="k.arg"
            class="key-arg-input"
            placeholder="子键(参数名等)"
            :disabled="readonly"
          />
          <a-button
            v-if="!readonly"
            danger
            type="text"
            size="small"
            @click="record.keys.splice(idx, 1)"
          >
            删除
          </a-button>
        </div>
        <a-button
          v-if="!readonly"
          type="dashed"
          size="small"
          @click="record.keys.push({ field: 'ip.src', arg: '' })"
        >
          + 添加维度
        </a-button>
      </fs-form-section>

      <fs-form-section title="前置条件" description="可选，留空表示所有请求都计数">
        <condition-editor v-model:value="record.conditions" :readonly="readonly" />
      </fs-form-section>

      <block-page-form-section
        v-if="record.mode === 'block'"
        :record="record"
        :readonly="readonly"
        switch-label="启用策略专属拦截页"
        description="关闭时使用站点或全局防护页面；命中本策略时优先使用此处配置"
      />
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

const keyFields = [
  { value: "ip.src", label: "客户端 IP" },
  { value: "http.uri.path", label: "请求路径" },
  { value: "http.host", label: "请求域名" },
  { value: "http.ua", label: "User-Agent" },
  { value: "http.query", label: "查询参数" },
  { value: "http.cookie", label: "Cookie 参数" },
  { value: "http.header", label: "请求头" },
];
const argFields = ["http.query", "http.cookie", "http.header"];

const batchConfig: BatchConfig = {
  modeOptions: modeFilterOptions,
  editFields: [
    commonBatchEditFields.enabled,
    commonBatchEditFields.mode,
    commonBatchEditFields.priority,
    commonBatchEditFields.window,
    commonBatchEditFields.threshold,
    commonBatchEditFields.siteIds,
  ],
};

const defaultSort: ResourceDefaultSort = { field: "priority", order: "asc" };

const listFilters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "策略名称 / 备注" },
  { key: "mode", label: "动作", type: "select", width: "200px", options: modeFilterOptions },
  { key: "enabled", label: "状态", type: "select", width: "140px", options: enabledFilterOptions },
  siteScopeFilterField,
];

const columns: ResourceColumn[] = [
  { title: "名称", dataIndex: "name", sorter: true },
  { title: "备注", dataIndex: "remark", ellipsis: true },
  { title: "优先级", dataIndex: "priority", width: 90, sorter: true },
  { title: "窗口(s)", dataIndex: "window", width: 90, sorter: true },
  { title: "阈值", dataIndex: "threshold", width: 90, sorter: true },
  { title: "动作", key: "mode", dataIndex: "mode", width: 110, slotCell: true, sorter: true },
  siteIdsColumn(),
  { title: "状态", key: "enabled", dataIndex: "enabled", width: 90, sorter: true },
];

const defaultRecord = () => ({
  name: "",
  remark: "",
  priority: 100,
  window: 60,
  threshold: 100,
  mode: "block",
  site_ids: [],
  enabled: true,
  keys: [{ field: "ip.src", arg: "" }],
  conditions: { logic: "and", conditions: [] },
  ...BLOCK_PAGE_FIELD_DEFAULTS,
});

function preparePayload(row: Record<string, any>) {
  if (!Array.isArray(row.keys) || row.keys.length < 1) {
    throw new Error("至少需要配置一个限速维度");
  }
  const hasCond = hasMatchingConditions(row.conditions);
  if (row.mode !== "observe" && !hasCond) {
    throw new Error("非观察模式必须配置至少一条匹配条件");
  }
  if (row.mode !== "block") {
    row.custom_block_page_enabled = false;
  }
  validateBlockPageOverride(row);
  return row;
}
</script>

<style scoped>
.site-select-block :deep(.ant-select) {
  width: 100%;
  min-width: 0;
}

.key-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.key-field-select {
  width: 200px;
  flex-shrink: 0;
}

.key-arg-input {
  width: 160px;
  flex-shrink: 0;
}
</style>
