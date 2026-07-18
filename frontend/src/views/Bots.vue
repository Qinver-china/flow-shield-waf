<template>
  <page-shell
    title="Bot 库"
    description="维护 Bot 识别库与分类，在防护规则中通过 bot.name / bot.category / bot.is_known 引用；日志自动写入 bot 维度"
  >
    <template #actions>
      <a-button
        v-if="activeTab === 'bots'"
        type="primary"
        @click="botCrudRef?.openCreate()"
      >
        新增 Bot
      </a-button>
      <a-button
        v-else
        type="primary"
        @click="categoryCrudRef?.openCreate()"
      >
        新增分类
      </a-button>
    </template>

    <a-tabs v-model:active-key="activeTab">
      <a-tab-pane key="bots" tab="Bot 库">
        <resource-crud
          ref="botCrudRef"
          embedded
          title="Bot 库"
          api-base="/api/v1/bots"
          :columns="botColumns"
          :filters="botFilters"
          :default-record="defaultBotRecord"
          :map-record="mapBotRecord"
          :prepare-payload="prepareBotPayload"
          name-field="name"
          detail-actions
          duplicatable
        >
          <template #cell="{ column, record }">
            <site-ids-cell v-if="column.key === 'site_ids'" :site-ids="record.site_ids" />
            <template v-else-if="column.key === 'category'">
              {{ categoryLabel(record.category) }}
            </template>
            <template v-else-if="column.key === 'pattern_count'">
              {{ record.pattern_count ?? (record.ua_patterns || []).length }}
            </template>
            <template v-else-if="column.key === 'is_builtin'">
              <a-tag v-if="record.is_builtin" color="blue">内置</a-tag>
              <span v-else class="muted">自定义</span>
            </template>
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
                <a-input
                  v-model:value="record.name"
                  :disabled="readonly || record.is_builtin"
                  placeholder="如 Googlebot"
                />
              </a-form-item>
              <a-form-item label="分类" required>
                <a-select
                  v-model:value="record.category"
                  :disabled="readonly"
                  :options="categoryOptions"
                />
              </a-form-item>
              <a-form-item label="生效站点（不选=全局）">
                <site-select v-model:value="record.site_ids" :readonly="readonly" class="site-select-block" />
              </a-form-item>
              <a-form-item label="备注">
                <a-input v-model:value="record.remark" :disabled="readonly" placeholder="可选" />
              </a-form-item>
            </fs-form-section>

            <fs-form-section
              title="UA 匹配模式"
              description="每行一条；支持子串匹配，或以 /pattern/flags 形式填写正则"
            >
              <a-textarea
                v-model:value="record._patternsText"
                :disabled="readonly || record.is_builtin"
                :rows="8"
                placeholder="Googlebot&#10;/curl/[i]&#10;python-requests"
              />
            </fs-form-section>

            <fs-form-section
              title="DNS 反向验证"
              description="预留能力：填写后可声明可信 Bot 的 DNS 后缀（如 .googlebot.com），首期仅保存不生效"
            >
              <a-input
                v-model:value="record.verify_dns_suffix"
                :disabled="readonly || record.is_builtin"
                placeholder="如 .googlebot.com（即将支持）"
              />
            </fs-form-section>
          </template>
        </resource-crud>
      </a-tab-pane>

      <a-tab-pane key="categories" tab="分类管理">
        <resource-crud
          ref="categoryCrudRef"
          embedded
          title="Bot 分类"
          api-base="/api/v1/bot-categories"
          :columns="categoryColumns"
          :filters="categoryFilters"
          :default-record="defaultCategoryRecord"
          :map-record="mapCategoryRecord"
          :prepare-payload="prepareCategoryPayload"
          name-field="label"
          detail-actions
        >
          <template #cell="{ column, record }">
            <template v-if="column.key === 'value'">
              <code>{{ record.value }}</code>
              <a-tag v-if="record.value === 'other'" color="purple" class="reserved-tag">系统预留</a-tag>
            </template>
            <template v-else-if="column.key === 'is_builtin'">
              <a-tag v-if="record.is_builtin" color="blue">内置</a-tag>
              <span v-else class="muted">自定义</span>
            </template>
          </template>

          <template #form="{ record, readonly, mode }">
            <fs-form-section title="分类信息">
              <a-form-item v-if="mode === 'create'" label="标识" required>
                <a-input
                  v-model:value="record.value"
                  :disabled="readonly"
                  placeholder="如 seo_tool（小写英文，创建后不可改）"
                />
                <p class="fs-hint">不可使用系统预留标识 other</p>
              </a-form-item>
              <a-form-item v-else label="标识">
                <a-input :value="record.value" disabled />
              </a-form-item>
              <a-form-item label="显示名称" required>
                <a-input v-model:value="record.label" :disabled="readonly" placeholder="如 SEO 工具" />
              </a-form-item>
              <a-form-item label="排序">
                <a-input-number v-model:value="record.sort_order" :disabled="readonly" :min="0" class="sort-input" />
              </a-form-item>
              <a-form-item label="备注">
                <a-input v-model:value="record.remark" :disabled="readonly" placeholder="可选" />
              </a-form-item>
            </fs-form-section>
          </template>
        </resource-crud>
      </a-tab-pane>
    </a-tabs>
  </page-shell>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { api } from "@/api";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import PageShell from "@/components/PageShell.vue";
import ResourceCrud from "@/components/ResourceCrud.vue";
import SiteIdsCell from "@/components/SiteIdsCell.vue";
import SiteSelect from "@/components/SiteSelect.vue";
import { siteIdsColumn } from "@/composables/useSiteOptions";
import { enabledFilterOptions } from "@/constants/resourceList";
import type { ResourceColumn, ResourceFilterField } from "@/types/resourceList";

const activeTab = ref("bots");
const botCrudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);
const categoryCrudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);

const categoryOptions = ref<{ label: string; value: string }[]>([]);

const botFilters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "名称 / UA 模式" },
  { key: "category", label: "分类", type: "select", options: [] },
  { key: "enabled", label: "状态", type: "select", options: enabledFilterOptions },
];

const botColumns: ResourceColumn[] = [
  { title: "名称", dataIndex: "name", sorter: true },
  { title: "分类", key: "category", dataIndex: "category", width: 110, slotCell: true },
  {
    title: "UA 模式",
    key: "pattern_count",
    dataIndex: "pattern_count",
    width: 88,
    slotCell: true,
  },
  siteIdsColumn(),
  { title: "类型", key: "is_builtin", width: 88, slotCell: true },
  { title: "状态", key: "enabled", dataIndex: "enabled", width: 90, sorter: true },
];

const categoryFilters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "标识 / 名称" },
];

const categoryColumns: ResourceColumn[] = [
  { title: "标识", key: "value", dataIndex: "value", width: 160, slotCell: true, sorter: true },
  { title: "显示名称", dataIndex: "label", sorter: true },
  { title: "排序", dataIndex: "sort_order", width: 80, sorter: true },
  { title: "类型", key: "is_builtin", width: 88, slotCell: true },
];

function categoryLabel(value: string) {
  return categoryOptions.value.find((o) => o.value === value)?.label || value;
}

function parseLines(text: string) {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
}

const defaultBotRecord = () => ({
  name: "",
  category: "other",
  enabled: true,
  site_ids: [] as number[],
  ua_patterns: [] as string[],
  verify_dns_suffix: "",
  remark: "",
  is_builtin: false,
  _patternsText: "",
});

function mapBotRecord(row: Record<string, any>) {
  return {
    ...row,
    site_ids: row.site_ids || [],
    _patternsText: row._patternsText ?? (row.ua_patterns || []).join("\n"),
  };
}

function prepareBotPayload(rec: Record<string, any>) {
  return {
    name: rec.name,
    category: rec.category,
    enabled: rec.enabled,
    site_ids: rec.site_ids?.length ? rec.site_ids : null,
    ua_patterns: parseLines(rec._patternsText || ""),
    verify_dns_suffix: rec.verify_dns_suffix || null,
    remark: rec.remark || null,
  };
}

const defaultCategoryRecord = () => ({
  value: "",
  label: "",
  sort_order: 50,
  remark: "",
});

function mapCategoryRecord(row: Record<string, any>) {
  return { ...row };
}

function prepareCategoryPayload(rec: Record<string, any>) {
  return {
    value: rec.value,
    label: rec.label,
    sort_order: rec.sort_order ?? 0,
    remark: rec.remark || null,
  };
}

async function loadCategoryOptions() {
  const resp = await api.get("/api/v1/bot-categories/options");
  categoryOptions.value = resp.data || [];
  const categoryFilter = botFilters.find((f) => f.key === "category");
  if (categoryFilter) {
    categoryFilter.options = categoryOptions.value;
  }
}

watch(activeTab, (tab) => {
  if (tab === "bots") {
    void loadCategoryOptions();
  }
});

onMounted(() => {
  void loadCategoryOptions();
});
</script>

<style scoped>
.site-select-block :deep(.ant-select) {
  width: 100%;
  min-width: 0;
}
.muted {
  color: var(--fs-text-muted, #94a3b8);
}
.reserved-tag {
  margin-left: 8px;
}
.sort-input {
  width: 120px;
}
</style>
