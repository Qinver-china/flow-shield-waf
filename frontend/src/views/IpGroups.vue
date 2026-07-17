<template>
  <page-shell
    title="IP 组管理"
    description="创建可复用的 IP / 网段集合，在防护条件中通过「包含 IP 组」「不包含 IP 组」引用"
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
      <template #form="{ record, readonly, mode }">
        <fs-form-section title="基本信息">
          <a-form-item label="名称" required>
            <a-input v-model:value="record.name" :disabled="readonly" placeholder="如：办公网、CDN 节点" />
          </a-form-item>
          <a-form-item label="备注">
            <a-input v-model:value="record.remark" :disabled="readonly" placeholder="可选" />
          </a-form-item>
        </fs-form-section>

        <fs-form-section
          v-if="!readonly && mode === 'create'"
          title="批量添加 IP"
          description="支持手动填写（一行一个）或导入文本文件；也可创建后再编辑补充"
        >
          <a-tabs v-model:active-key="entryTab">
            <a-tab-pane key="manual" tab="手动填写">
              <a-textarea
                v-model:value="record._entryText"
                :rows="8"
                placeholder="每行一个 IP 或 CIDR，例如：&#10;1.2.3.4&#10;10.0.0.0/8&#10;# 以 # 开头的行会被忽略"
              />
            </a-tab-pane>
            <a-tab-pane key="import" tab="导入文件">
              <a-upload
                :before-upload="(file) => onCreateImport(record, file)"
                :show-upload-list="false"
                accept=".txt,.csv,text/plain"
              >
                <a-button>选择文本文件</a-button>
              </a-upload>
              <p v-if="record._importFileName" class="fs-hint">
                已选择：{{ record._importFileName }}（{{ parseLines(record._entryText || "").length }} 条）
              </p>
              <p class="fs-hint">文件编码需为 UTF-8，每行一个 IP 或网段</p>
            </a-tab-pane>
          </a-tabs>
        </fs-form-section>

        <fs-form-section
          v-else-if="!readonly && record.id"
          title="批量添加 IP"
          description="向当前 IP 组追加条目，不会覆盖已有数据"
        >
          <a-tabs v-model:active-key="entryTab">
            <a-tab-pane key="manual" tab="手动填写">
              <a-textarea
                v-model:value="record._entryText"
                :rows="6"
                placeholder="每行一个 IP 或 CIDR"
              />
              <a-button
                type="primary"
                class="batch-btn"
                :loading="batchLoading"
                :disabled="!record._entryText?.trim()"
                @click="submitBatch(record)"
              >
                追加到 IP 组
              </a-button>
            </a-tab-pane>
            <a-tab-pane key="import" tab="导入文件">
              <a-upload
                :custom-request="(opt) => importFile(record, opt)"
                :show-upload-list="false"
                accept=".txt,.csv,text/plain"
              >
                <a-button :loading="batchLoading">选择并导入</a-button>
              </a-upload>
              <p class="fs-hint">导入后将自动追加到当前 IP 组</p>
            </a-tab-pane>
          </a-tabs>
        </fs-form-section>

        <fs-form-section title="IP 条目" :description="entriesDescription(record)">
          <div v-if="readonly || !record.id" class="entry-preview">
            <template v-if="displayEntries(record).length">
              <a-tag v-for="item in displayEntries(record)" :key="item" class="entry-tag">
                {{ item }}
              </a-tag>
            </template>
            <a-empty v-else description="暂无 IP 条目" :image-style="{ height: '48px' }" />
          </div>
          <div v-else class="entry-editor">
            <a-textarea
              v-model:value="record._entriesText"
              :rows="10"
              placeholder="每行一个 IP 或 CIDR，保存时将覆盖全部条目"
            />
          </div>
        </fs-form-section>
      </template>
    </resource-crud>
  </page-shell>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { message } from "ant-design-vue";
import { api } from "@/api";
import FsFormSection from "@/components/FsFormSection.vue";
import PageShell from "@/components/PageShell.vue";
import ResourceCrud from "@/components/ResourceCrud.vue";
import type { ResourceColumn, ResourceFilterField } from "@/types/resourceList";

const entryTab = ref("manual");
const batchLoading = ref(false);
const crudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);

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
  _entryText: "",
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
  if (record._entriesText != null && record._entriesText !== "") {
    return parseLines(record._entriesText);
  }
  return record.entries || [];
}

function entriesDescription(record: any) {
  const count = displayEntries(record).length;
  return count ? `共 ${count} 条` : "创建时可留空，稍后补充";
}

function mapRecord(row: Record<string, any>) {
  return {
    ...row,
    _entryText: row._entryText ?? "",
    _entriesText: row._entriesText ?? (row.entries || []).join("\n"),
    _importFileName: row._importFileName ?? "",
  };
}

function preparePayload(rec: Record<string, any>) {
  const payload: Record<string, unknown> = {
    name: rec.name,
    remark: rec.remark || null,
  };
  if (rec.id) {
    payload.entries = parseLines(rec._entriesText || "");
  } else {
    payload.entries = parseLines(rec._entryText || "");
  }
  return payload;
}

function onCreateImport(record: Record<string, any>, file: File) {
  const reader = new FileReader();
  reader.onload = () => {
    const text = String(reader.result || "");
    const existing = parseLines(record._entryText || "");
    const merged = [...existing, ...parseLines(text)];
    record._entryText = merged.join("\n");
    record._importFileName = file.name;
  };
  reader.readAsText(file);
  return false;
}

async function submitBatch(record: any) {
  const lines = parseLines(record._entryText || "");
  if (!lines.length) {
    message.warning("请填写至少一条 IP");
    return;
  }
  batchLoading.value = true;
  try {
    const resp = await api.post(`/api/v1/ip-groups/${record.id}/entries/batch`, {
      entries: lines,
    });
    record.entries = resp.data.entries || [];
    record.entry_count = resp.data.entry_count;
    record._entriesText = (record.entries || []).join("\n");
    record._entryText = "";
    message.success(`已追加 ${lines.length} 条（去重后以实际条目数为准）`);
  } finally {
    batchLoading.value = false;
  }
}

async function importFile(record: any, opt: { file: File | Blob; onSuccess?: (v: unknown) => void; onError?: (e: Error) => void }) {
  const file = opt.file as File;
  if (!record.id) {
    opt.onError?.(new Error("no id"));
    return;
  }
  batchLoading.value = true;
  try {
    const form = new FormData();
    form.append("file", file);
    const resp = await api.post(`/api/v1/ip-groups/${record.id}/entries/import`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    record.entries = resp.data.entries || [];
    record.entry_count = resp.data.entry_count;
    record._entriesText = (record.entries || []).join("\n");
    message.success("导入成功");
    opt.onSuccess?.(resp.data);
  } catch (err) {
    opt.onError?.(err as Error);
  } finally {
    batchLoading.value = false;
  }
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
.entry-editor :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}
.batch-btn {
  margin-top: 10px;
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
