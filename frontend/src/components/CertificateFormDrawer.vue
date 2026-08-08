<template>
  <fs-form-drawer
    :open="open"
    title="SSL 证书"
    :subtitle="certificateId ? `#${certificateId}` : undefined"
    :mode="certificateId ? 'edit' : 'create'"
    :width="760"
    :z-index="zIndex"
    :loading="detailLoading"
    :confirm-loading="saving"
    @update:open="emit('update:open', $event)"
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

      <fs-form-section
        title="到期前通知"
        description="到期前 7 天每日会通知一次"
      >
        <template #extra>
          <a-switch v-model:checked="form.expiry_notify_enabled" />
        </template>
        <a-form-item v-if="form.expiry_notify_enabled" label="通知通道" required>
          <a-select
            v-model:value="form.expiry_notify_channel_ids"
            mode="multiple"
            placeholder="选择已配置的通知通道"
            allow-clear
            option-filter-prop="label"
            style="width: 100%"
          >
            <a-select-option
              v-for="ch in channels"
              :key="ch.id"
              :value="ch.id"
              :label="ch.name"
              :disabled="!ch.enabled"
            >
              {{ ch.name }}（{{ channelTypeLabel(ch.channel_type) }}）
            </a-select-option>
          </a-select>
          <p class="fs-hint is-inline">请先在「系统设置 → 通知通道」中配置邮件等通道。</p>
        </a-form-item>
      </fs-form-section>

      <fs-form-section title="证书内容" description="支持粘贴 PEM 文本或上传文件">
        <a-tabs v-model:activeKey="importMode">
          <a-tab-pane key="paste" tab="粘贴内容">
            <a-form-item label="证书 (PEM)" required>
              <a-textarea
                v-model:value="form.cert_content"
                :rows="6"
                placeholder="-----BEGIN CERTIFICATE-----"
                class="fs-code-textarea"
              />
            </a-form-item>
            <a-form-item label="密钥 (KEY)" required>
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
            <p v-if="certificateId" class="fs-hint">未选择新文件时，将保留当前证书内容。</p>
          </a-tab-pane>
        </a-tabs>
      </fs-form-section>
    </a-form>
  </fs-form-drawer>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { message, type UploadProps } from "ant-design-vue";
import { api } from "@/api";
import FsFormDrawer from "@/components/FsFormDrawer.vue";
import FsFormSection from "@/components/FsFormSection.vue";

export interface CertificateSaved {
  id: number;
  name: string;
  domains: string | null;
  not_after?: string | null;
}

interface NotificationChannelItem {
  id: number;
  name: string;
  channel_type: string;
  enabled: boolean;
}

interface CertificateDetail {
  id: number;
  name: string;
  remark: string | null;
  cert_content: string;
  key_content: string;
  expiry_notify_enabled?: boolean;
  expiry_notify_channel_ids?: number[];
}

const props = withDefaults(
  defineProps<{
    open: boolean;
    /** 传入时为更新模式，否则为导入/新建 */
    certificateId?: number | null;
    zIndex?: number;
  }>(),
  {
    certificateId: null,
    zIndex: undefined,
  },
);

const emit = defineEmits<{
  "update:open": [boolean];
  saved: [cert: CertificateSaved];
}>();

const detailLoading = ref(false);
const saving = ref(false);
const importMode = ref<"paste" | "upload">("paste");
const channels = ref<NotificationChannelItem[]>([]);

const form = reactive({
  name: "",
  remark: "",
  cert_content: "",
  key_content: "",
  expiry_notify_enabled: false,
  expiry_notify_channel_ids: [] as number[],
});

const certFile = ref<File | null>(null);
const keyFile = ref<File | null>(null);
const certFileList = ref<UploadProps["fileList"]>([]);
const keyFileList = ref<UploadProps["fileList"]>([]);

function channelTypeLabel(type: string) {
  if (type === "email") return "邮件";
  if (type === "webhook") return "Webhook";
  if (type === "dingtalk") return "钉钉";
  if (type === "sms") return "短信";
  return type;
}

function resetForm() {
  form.name = "";
  form.remark = "";
  form.cert_content = "";
  form.key_content = "";
  form.expiry_notify_enabled = false;
  form.expiry_notify_channel_ids = [];
  certFile.value = null;
  keyFile.value = null;
  certFileList.value = [];
  keyFileList.value = [];
  importMode.value = "paste";
}

async function loadChannels() {
  try {
    const resp = await api.get<NotificationChannelItem[]>("/api/v1/notification-channels");
    channels.value = resp.data || [];
  } catch {
    channels.value = [];
  }
}

async function loadDetail(id: number) {
  detailLoading.value = true;
  try {
    const resp = await api.get<CertificateDetail>(`/api/v1/certificates/${id}`);
    const detail = resp.data;
    form.name = detail.name;
    form.remark = detail.remark || "";
    form.cert_content = detail.cert_content;
    form.key_content = detail.key_content;
    form.expiry_notify_enabled = Boolean(detail.expiry_notify_enabled);
    form.expiry_notify_channel_ids = [...(detail.expiry_notify_channel_ids || [])];
  } finally {
    detailLoading.value = false;
  }
}

watch(
  () => props.open,
  async (open) => {
    if (!open) return;
    resetForm();
    await loadChannels();
    if (props.certificateId) {
      await loadDetail(props.certificateId);
    }
  },
);

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
    if (props.certificateId && form.cert_content.trim() && form.key_content.trim()) {
      return {
        cert: form.cert_content,
        key: form.key_content,
      };
    }
    if (!props.certificateId) {
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

function notifyPayload() {
  return {
    expiry_notify_enabled: form.expiry_notify_enabled,
    expiry_notify_channel_ids: form.expiry_notify_enabled
      ? [...form.expiry_notify_channel_ids]
      : [],
  };
}

async function save() {
  if (!form.name.trim()) {
    message.warning("请填写证书名称");
    return;
  }
  if (form.expiry_notify_enabled && !form.expiry_notify_channel_ids.length) {
    message.warning("启用到期前通知时请选择通知通道");
    return;
  }

  const contents = await resolveCertContents();
  if (!contents) return;

  saving.value = true;
  try {
    let saved: CertificateSaved;
    const notify = notifyPayload();
    if (props.certificateId) {
      const resp = await api.put<CertificateSaved>(`/api/v1/certificates/${props.certificateId}`, {
        name: form.name.trim(),
        remark: form.remark || null,
        cert_content: contents.cert,
        key_content: contents.key,
        ...notify,
      });
      saved = resp.data;
    } else if (importMode.value === "upload") {
      const fd = new FormData();
      fd.append("name", form.name.trim());
      if (form.remark) fd.append("remark", form.remark);
      fd.append("expiry_notify_enabled", String(notify.expiry_notify_enabled));
      if (notify.expiry_notify_channel_ids.length) {
        fd.append("expiry_notify_channel_ids", JSON.stringify(notify.expiry_notify_channel_ids));
      }
      fd.append("cert_file", certFile.value!);
      fd.append("key_file", keyFile.value!);
      const resp = await api.upload<CertificateSaved>("/api/v1/certificates/upload", fd);
      saved = resp.data;
    } else {
      const resp = await api.post<CertificateSaved>("/api/v1/certificates", {
        name: form.name.trim(),
        remark: form.remark || null,
        cert_content: contents.cert,
        key_content: contents.key,
        ...notify,
      });
      saved = resp.data;
    }
    message.success("保存成功");
    emit("update:open", false);
    emit("saved", saved);
  } catch {
    // interceptor shows error
  } finally {
    saving.value = false;
  }
}
</script>
