<template>
  <page-shell title="证书管理" description="导入与管理 SSL/TLS 证书，供站点 HTTPS 使用">
    <template #actions>
      <a-button type="primary" @click="openCreate">导入证书</a-button>
    </template>

    <list-filter-bar
      :fields="listFilters"
      :model="filterValues"
      @change="onFilterChange"
      @reset="resetFilters"
    />

    <fs-data-table
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="pagination"
      api-base="/api/v1/certificates"
      :batch="{ allowDelete: true, enableToggle: false }"
      :scroll="{ x: 720 }"
      @change="onTableChange"
      @refresh="fetchList"
    >
      <template #bodyCell="{ column, record, text }">
        <template v-if="column.key === 'not_after'">
          <span :class="expiryClass(record.not_after)">{{ formatTime(text) }}</span>
        </template>
        <template v-else-if="column.key === '__actions'">
          <a @click="openUpdate(record)">更新证书</a>
          <a-divider type="vertical" />
          <a-popconfirm title="确认删除该证书?" @confirm="remove(record.id)">
            <a class="danger">删除</a>
          </a-popconfirm>
        </template>
        <template v-else>
          {{ text ?? "-" }}
        </template>
      </template>
    </fs-data-table>

    <fs-form-drawer
      v-model:open="modalOpen"
      title="SSL 证书"
      :subtitle="editingId ? `#${editingId}` : undefined"
      :mode="editingId ? 'edit' : 'create'"
      :width="760"
      :loading="detailLoading"
      :confirm-loading="saving"
      @ok="save"
    >
      <a-form layout="vertical">
          <fs-form-section title="基本信息">
            <a-form-item label="证书名称" required>
              <a-input v-model:value="form.name" placeholder="" />
            </a-form-item>
            <a-form-item label="备注">
              <a-input v-model:value="form.remark" placeholder="可选" />
            </a-form-item>
          </fs-form-section>

          <fs-form-section title="证书内容" description="支持粘贴 PEM 文本或上传文件">
            <a-tabs v-model:activeKey="importMode">
              <a-tab-pane key="paste" tab="粘贴内容">
                <a-form-item label="证书内容 (PEM)" required>
                  <a-textarea
                    v-model:value="form.cert_content"
                    :rows="6"
                    placeholder="-----BEGIN CERTIFICATE-----"
                    class="fs-code-textarea"
                  />
                </a-form-item>
                <a-form-item label="私钥内容 (PEM)" required>
                  <a-textarea
                    v-model:value="form.key_content"
                    :rows="6"
                    placeholder="-----BEGIN PRIVATE KEY-----"
                    class="fs-code-textarea"
                  />
                </a-form-item>
              </a-tab-pane>
              <a-tab-pane key="upload" tab="上传文件">
                <a-form-item label="证书文件 (.pem / .crt)" required>
                  <a-upload
                    :before-upload="onCertFile"
                    :max-count="1"
                    :file-list="certFileList"
                    @remove="clearCertFile"
                  >
                    <a-button>选择证书文件</a-button>
                  </a-upload>
                </a-form-item>
                <a-form-item label="私钥文件 (.key / .pem)" required>
                  <a-upload
                    :before-upload="onKeyFile"
                    :max-count="1"
                    :file-list="keyFileList"
                    @remove="clearKeyFile"
                  >
                    <a-button>选择私钥文件</a-button>
                  </a-upload>
                </a-form-item>
                <p v-if="editingId" class="fs-hint">未选择新文件时，将保留当前证书内容。</p>
              </a-tab-pane>
            </a-tabs>
          </fs-form-section>
        </a-form>
    </fs-form-drawer>
  </page-shell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { message, type UploadProps } from "ant-design-vue";
import { api } from "@/api";
import FsDataTable from "@/components/FsDataTable.vue";
import FsFormDrawer from "@/components/FsFormDrawer.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import ListFilterBar from "@/components/ListFilterBar.vue";
import PageShell from "@/components/PageShell.vue";
import { certificateExpiryFilterOptions } from "@/constants/resourceList";
import { formatDateTime, parseUtc } from "@/utils/datetime";
import type { ResourceFilterField } from "@/types/resourceList";

interface CertificateRow {
  id: number;
  name: string;
  domains: string | null;
  not_before: string | null;
  not_after: string | null;
  remark: string | null;
}

interface CertificateDetail extends CertificateRow {
  cert_content: string;
  key_content: string;
}

const listFilters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "名称 / 域名 / 备注" },
  {
    key: "expiry",
    label: "到期状态",
    type: "select",
    width: "180px",
    options: certificateExpiryFilterOptions,
  },
];

const columns = computed(() => [
  {
    title: "名称",
    dataIndex: "name",
    sorter: true,
    sortOrder: sortField.value === "name" ? (sortOrder.value === "asc" ? "ascend" : "descend") : undefined,
  },
  { title: "域名", dataIndex: "domains", ellipsis: true },
  {
    title: "到期时间",
    key: "not_after",
    dataIndex: "not_after",
    width: 180,
    sorter: true,
    sortOrder:
      sortField.value === "not_after" ? (sortOrder.value === "asc" ? "ascend" : "descend") : undefined,
  },
  { title: "备注", dataIndex: "remark", ellipsis: true },
  { title: "操作", key: "__actions", width: 180 },
]);

const rows = ref<CertificateRow[]>([]);
const loading = ref(false);
const detailLoading = ref(false);
const saving = ref(false);
const modalOpen = ref(false);
const editingId = ref<number | null>(null);
const importMode = ref<"paste" | "upload">("paste");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const filterValues = reactive<Record<string, unknown>>({});
const sortField = ref<string | undefined>();
const sortOrder = ref<"asc" | "desc" | undefined>("desc");

const form = reactive({
  name: "",
  remark: "",
  cert_content: "",
  key_content: "",
});

const certFile = ref<File | null>(null);
const keyFile = ref<File | null>(null);
const certFileList = ref<UploadProps["fileList"]>([]);
const keyFileList = ref<UploadProps["fileList"]>([]);

const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showTotal: (t: number) => `共 ${t} 条`,
}));

function resetForm() {
  form.name = "";
  form.remark = "";
  form.cert_content = "";
  form.key_content = "";
  certFile.value = null;
  keyFile.value = null;
  certFileList.value = [];
  keyFileList.value = [];
  importMode.value = "paste";
}

function formatTime(value: string | null) {
  return formatDateTime(value);
}

function expiryClass(notAfter: string | null) {
  if (!notAfter) return "";
  const diff = parseUtc(notAfter).valueOf() - Date.now();
  if (diff < 0) return "expired";
  if (diff < 30 * 24 * 3600 * 1000) return "soon";
  return "";
}

async function fetchList() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize.value,
    };
    if (sortField.value && sortOrder.value) {
      params.sort_by = sortField.value;
      params.sort_order = sortOrder.value;
    }
    for (const field of listFilters) {
      const value = filterValues[field.key];
      if (value !== undefined && value !== null && value !== "") {
        params[field.key] = value;
      }
    }
    const resp = await api.get("/api/v1/certificates", params);
    rows.value = resp.data.items;
    total.value = resp.data.total;
  } finally {
    loading.value = false;
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
    sortField.value = undefined;
    sortOrder.value = "desc";
  }
  fetchList();
}

function onFilterChange() {
  page.value = 1;
  fetchList();
}

function resetFilters() {
  for (const field of listFilters) {
    filterValues[field.key] = undefined;
  }
  page.value = 1;
  fetchList();
}

function openCreate() {
  editingId.value = null;
  resetForm();
  modalOpen.value = true;
}

async function openUpdate(row: CertificateRow) {
  editingId.value = row.id;
  resetForm();
  modalOpen.value = true;
  detailLoading.value = true;
  try {
    const resp = await api.get<CertificateDetail>(`/api/v1/certificates/${row.id}`);
    const detail = resp.data;
    form.name = detail.name;
    form.remark = detail.remark || "";
    form.cert_content = detail.cert_content;
    form.key_content = detail.key_content;
  } finally {
    detailLoading.value = false;
  }
}

const onCertFile: UploadProps["beforeUpload"] = (file) => {
  certFile.value = file as File;
  certFileList.value = [file];
  return false;
};

const onKeyFile: UploadProps["beforeUpload"] = (file) => {
  keyFile.value = file as File;
  keyFileList.value = [file];
  return false;
};

function clearCertFile() {
  certFile.value = null;
  certFileList.value = [];
}

function clearKeyFile() {
  keyFile.value = null;
  keyFileList.value = [];
}

async function readFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

async function resolveCertContents(): Promise<{ cert: string; key: string } | null> {
  if (importMode.value === "upload") {
    if (certFile.value && keyFile.value) {
      return {
        cert: await readFile(certFile.value),
        key: await readFile(keyFile.value),
      };
    }
    if (editingId.value && form.cert_content.trim() && form.key_content.trim()) {
      return {
        cert: form.cert_content,
        key: form.key_content,
      };
    }
    if (!editingId.value) {
      message.warning("请上传证书文件和私钥文件");
      return null;
    }
    message.warning("请选择新的证书文件和私钥文件");
    return null;
  }

  if (!form.cert_content.trim() || !form.key_content.trim()) {
    message.warning("请填写证书和私钥内容");
    return null;
  }
  return {
    cert: form.cert_content,
    key: form.key_content,
  };
}

async function save() {
  if (!form.name.trim()) {
    message.warning("请填写证书名称");
    return;
  }

  const contents = await resolveCertContents();
  if (!contents) return;

  saving.value = true;
  try {
    if (editingId.value) {
      await api.put(`/api/v1/certificates/${editingId.value}`, {
        name: form.name.trim(),
        remark: form.remark || null,
        cert_content: contents.cert,
        key_content: contents.key,
      });
    } else if (importMode.value === "upload") {
      const fd = new FormData();
      fd.append("name", form.name.trim());
      if (form.remark) fd.append("remark", form.remark);
      fd.append("cert_file", certFile.value!);
      fd.append("key_file", keyFile.value!);
      await api.upload("/api/v1/certificates/upload", fd);
    } else {
      await api.post("/api/v1/certificates", {
        name: form.name.trim(),
        remark: form.remark || null,
        cert_content: contents.cert,
        key_content: contents.key,
      });
    }
    message.success("保存成功");
    modalOpen.value = false;
    fetchList();
  } catch {
    // interceptor shows error
  } finally {
    saving.value = false;
  }
}

async function remove(id: number) {
  await api.del(`/api/v1/certificates/${id}`);
  message.success("已删除");
  fetchList();
}

onMounted(fetchList);
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.toolbar h3 {
  margin: 0;
}
.danger {
  color: #ef4444;
}
.expired {
  color: #ef4444;
}
.soon {
  color: #f59e0b;
}
</style>
