<template>
  <page-shell
    title="IP 组管理"
    description="创建可复用的 IPv4 / IPv6 地址或网段集合，在防护条件中通过「包含 IP 组」「不包含 IP 组」引用"
  >
    <template #actions>
      <a-button type="primary" @click="crudRef?.openCreate()">新增 IP 组</a-button>
    </template>
    <resource-crud
      ref="crudRef"
      embedded
      title="IP 组"
      api-base="/api/v1/ip-groups"
      :columns="columns"
      :filters="listFilters"
      :default-record="defaultRecord"
      :map-record="mapRecord"
      :prepare-payload="preparePayload"
      :batch="batchConfig"
      :show-view-json="false"
      name-field="name"
      detail-actions
      duplicatable
    >
      <template #cell="{ column, record }">
        <template v-if="column.key === 'entry_count'">
          {{ entryCount(record) }}
        </template>
        <template v-else-if="column.key === 'ip_entries'">
          <div
            v-if="(record.entries || []).length"
            class="ip-detail-preview"
            :title="(record.entries || []).join('、')"
          >
            {{ formatIpPreview(record.entries) }}
          </div>
          <span v-else class="ip-detail-empty">—</span>
        </template>
      </template>
      <template #form="{ record, readonly }">
        <fs-form-section title="基本信息">
          <a-form-item label="名称" required>
            <a-input v-model:value="record.name" :disabled="readonly" placeholder="如：办公网、CDN 节点" />
          </a-form-item>
          <a-form-item label="备注">
            <a-textarea
              v-model:value="record.remark"
              :disabled="readonly"
              placeholder="可选"
              :auto-size="{ minRows: 1, maxRows: 6 }"
            />
          </a-form-item>
        </fs-form-section>

        <fs-form-section title="IP 条目" :description="entriesDescription(record, readonly)">
          <div v-if="readonly" class="entry-preview">
            <template v-if="displayEntries(record).length">
              <a-tag v-for="item in displayEntries(record)" :key="item" class="entry-tag">
                {{ item }}
              </a-tag>
            </template>
            <a-empty v-else description="暂无 IP 条目" :image-style="{ height: '48px' }" />
          </div>
           <a-tabs v-else v-model:active-key="entryTab">
            <a-tab-pane key="manual" tab="手动编辑">
              <a-textarea
                v-model:value="record._entriesText"
                :rows="10"
                class="entry-editor"
                placeholder="每行一个 IPv4 / IPv6 或 CIDR，例如：&#10;1.2.3.4&#10;10.0.0.0/8&#10;2001:db8::1&#10;2001:db8::/32&#10;# 以 # 开头的行会被忽略&#10;&#10;可直接增删行；保存时覆盖全部条目"
              />
            </a-tab-pane>
            <a-tab-pane key="import" tab="导入文件">
              <a-upload
                :before-upload="(file) => onImportFile(record, file)"
                :show-upload-list="false"
                accept=".txt,.csv,text/plain"
              >
                <a-button>选择文本文件</a-button>
              </a-upload>
              <p v-if="record._importFileName" class="fs-hint">
                已导入：{{ record._importFileName }}（当前共 {{ displayEntries(record).length }} 条，保存后生效）
              </p>
              <p class="fs-hint">
                文件编码需为 UTF-8，每行一个 IPv4 / IPv6 地址或网段；导入内容会合并进上方列表（去重），不会立刻覆盖已有条目，请检查后点保存
              </p>
            </a-tab-pane>
          </a-tabs>
        </fs-form-section>
      </template>
    </resource-crud>
  </page-shell>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { message } from "ant-design-vue";
import FsFormSection from "@/components/FsFormSection.vue";
import PageShell from "@/components/PageShell.vue";
import ResourceCrud from "@/components/ResourceCrud.vue";
import type { BatchConfig } from "@/types/batch";
import type { ResourceColumn, ResourceFilterField } from "@/types/resourceList";

const entryTab = ref("manual");
const crudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);

const batchConfig: BatchConfig = {
  allowDelete: true,
};

const listFilters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "名称 / IP 地址" },
];

const columns: ResourceColumn[] = [
  { title: "名称", dataIndex: "name", sorter: true },
  {
    title: "条目数",
    key: "entry_count",
    dataIndex: "entry_count",
    width: 88,
    slotCell: true,
    customRender: ({ record }) => entryCount(record),
  },
  {
    title: "IP 明细",
    key: "ip_entries",
    slotCell: true,
  },
];

function entryCount(record: Record<string, unknown>) {
  if (typeof record.entry_count === "number") return record.entry_count;
  const entries = record.entries;
  return Array.isArray(entries) ? entries.length : 0;
}

function formatIpPreview(entries: unknown) {
  if (!Array.isArray(entries) || !entries.length) return "";
  return entries.join("、");
}

const defaultRecord = () => ({
  name: "",
  remark: "",
  entries: [] as string[],
  _entriesText: "",
  _importFileName: "",
});

function parseLines(text: string) {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
}

function displayEntries(record: any) {
  if (record._entriesText != null) {
    return parseLines(record._entriesText);
  }
  return record.entries || [];
}

function entriesDescription(record: any, readonly?: boolean) {
  const count = displayEntries(record).length;
  if (readonly) return count ? `共 ${count} 条` : "暂无条目";
  if (count) return `共 ${count} 条 · 可增删行或导入文件，保存时覆盖全部条目`;
  return "支持手动编辑（一行一个）或导入文本文件";
}

function mapRecord(row: Record<string, any>) {
  return {
    ...row,
    _entriesText: row._entriesText ?? (row.entries || []).join("\n"),
    _importFileName: row._importFileName ?? "",
  };
}

function preparePayload(rec: Record<string, any>) {
  return {
    name: rec.name,
    remark: rec.remark || null,
    entries: parseLines(rec._entriesText || ""),
  };
}

function onImportFile(record: Record<string, any>, file: File) {
  const reader = new FileReader();
  reader.onload = () => {
    const text = String(reader.result || "");
    const existing = parseLines(record._entriesText || "");
    const imported = parseLines(text);
    if (!imported.length) {
      message.warning("文件中没有有效的 IP 条目");
      return;
    }
    const merged = [...new Set([...existing, ...imported])];
    record._entriesText = merged.join("\n");
    record._importFileName = file.name;
    entryTab.value = "manual";
    message.success(`已合并 ${imported.length} 条，请检查后保存`);
  };
  reader.readAsText(file);
  return false;
}
</script>

<style scoped>
.entry-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.entry-tag {
  margin: 0;
}
:deep(textarea.entry-editor) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}
.ip-detail-preview {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  line-height: 1.5;
  max-height: 3em;
  word-break: break-all;
  color: var(--fs-text-secondary, #64748b);
  font-size: 13px;
}
.ip-detail-empty {
  color: var(--fs-text-muted, #94a3b8);
}
</style>
