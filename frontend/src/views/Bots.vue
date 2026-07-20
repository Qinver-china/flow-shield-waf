<template>
  <page-shell
    title="Bot 库"
    description="维护 Bot 识别库与分类，在防护规则中通过 bot.name / bot.category / bot.is_known 引用；日志自动写入 bot 维度"
  >
    <a-alert
      v-if="vendoredInfo"
      type="info"
      show-icon
      class="vendored-banner"
    >
      <template #message>
        <div class="vendored-head">
          <span>Vendored 爬虫规则（JayBizzle/Crawler-Detect）</span>
          <a-button
            size="small"
            :loading="vendoredSyncing"
            @click="syncVendored"
          >
            立即更新 vendored
          </a-button>
        </div>
      </template>
      <template #description>
        <div v-if="vendoredInfo.installed" class="vendored-meta">
          <span>上游：{{ vendoredInfo.upstream_repo }}@{{ vendoredInfo.upstream_branch }}</span>
          <span v-if="vendoredInfo.upstream_commit">Commit：{{ shortCommit(vendoredInfo.upstream_commit) }}</span>
          <span>爬虫规则：{{ vendoredInfo.crawlers_count }} 条</span>
          <span>排除规则：{{ vendoredInfo.exclusions_count }} 条</span>
          <span>上次更新：{{ formatTime(vendoredInfo.updated_at) }}</span>
          <span>下次自动更新：{{ formatTime(vendoredInfo.next_auto_update_at) }}</span>
          <span>自动更新周期：{{ vendoredInfo.auto_update_days }} 天</span>
        </div>
        <div v-else class="vendored-meta">
          尚未安装 vendored 规则，可点击「立即更新 vendored」从上游拉取。
        </div>
      </template>
    </a-alert>

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
            <template v-if="column.key === 'category'">
              {{ categoryLabel(record.category) }}
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
import { computed, onMounted, ref, watch } from "vue";
import { message } from "ant-design-vue";
import { api } from "@/api";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import PageShell from "@/components/PageShell.vue";
import ResourceCrud from "@/components/ResourceCrud.vue";
import { enabledFilterOptions } from "@/constants/resourceList";
import type { ResourceColumn, ResourceFilterField } from "@/types/resourceList";

const activeTab = ref("bots");
const botCrudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);
const categoryCrudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);

const categoryOptions = ref<{ label: string; value: string }[]>([]);

type VendoredInfo = {
  installed: boolean;
  upstream_repo: string;
  upstream_branch: string;
  upstream_commit?: string | null;
  crawlers_count?: number;
  exclusions_count?: number;
  updated_at?: string | null;
  next_auto_update_at?: string | null;
  auto_update_days?: number;
  source?: string | null;
};

const vendoredInfo = ref<VendoredInfo | null>(null);
const vendoredSyncing = ref(false);

function shortCommit(commit?: string | null) {
  if (!commit) return "—";
  return commit.slice(0, 8);
}

function formatTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

async function loadVendoredInfo() {
  const resp = await api.get("/api/v1/bots/vendored");
  vendoredInfo.value = resp.data || null;
}

async function syncVendored() {
  vendoredSyncing.value = true;
  try {
    const resp = await api.post("/api/v1/bots/vendored/sync");
    if (resp.data?.updated === false) {
      message.info("当前未到自动更新周期，已强制检查完成");
    } else {
      message.success("vendored 规则已更新并下发到引擎");
    }
    await loadVendoredInfo();
  } catch (err: any) {
    message.error(err?.response?.data?.message || "更新 vendored 规则失败");
  } finally {
    vendoredSyncing.value = false;
  }
}

const botFilters = computed<ResourceFilterField[]>(() => [
  { key: "q", label: "搜索", type: "search", placeholder: "名称 / UA 模式" },
  {
    key: "category",
    label: "分类",
    type: "select",
    multiple: true,
    width: "280px",
    options: categoryOptions.value,
  },
  { key: "enabled", label: "状态", type: "select", options: enabledFilterOptions },
]);

const botColumns: ResourceColumn[] = [
  { title: "名称", dataIndex: "name", sorter: true },
  { title: "分类", key: "category", dataIndex: "category", width: 110, slotCell: true },
  { title: "备注", dataIndex: "remark", ellipsis: true },
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
  { title: "备注", dataIndex: "remark", ellipsis: true },
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
  ua_patterns: [] as string[],
  verify_dns_suffix: "",
  remark: "",
  is_builtin: false,
  _patternsText: "",
});

function mapBotRecord(row: Record<string, any>) {
  return {
    ...row,
    _patternsText: row._patternsText ?? (row.ua_patterns || []).join("\n"),
  };
}

function prepareBotPayload(rec: Record<string, any>) {
  return {
    name: rec.name,
    category: rec.category,
    enabled: rec.enabled,
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
}

watch(activeTab, (tab) => {
  if (tab === "bots") {
    void loadCategoryOptions();
  }
});

onMounted(() => {
  void loadCategoryOptions();
  void loadVendoredInfo();
});
</script>

<style scoped>
.vendored-banner {
  margin-bottom: 16px;
}
.vendored-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.vendored-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  color: var(--fs-text-muted, #94a3b8);
  font-size: 13px;
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
