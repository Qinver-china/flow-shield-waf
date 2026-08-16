<template>
  <fs-form-drawer :open="open" title="SSL 证书" :subtitle="certificateId ? `#${certificateId}` : undefined"
    :mode="certificateId ? 'edit' : 'create'" :width="820" :z-index="zIndex"
    :loading="isPanelImport ? panelStatus.loading : detailLoading"
    :confirm-loading="isPanelImport ? panelStatus.importing : saving"
    :ok-text="drawerOkText" :hide-ok="isPanelImport ? !panelStatus.canImport : false"
    @update:open="emit('update:open', $event)" @ok="save">
    <a-form layout="vertical">
      <template v-if="!isPanelImport">
        <fs-form-section title="基本信息">
          <a-form-item label="证书名称" :required="!isAcmeIssue">
            <a-input v-model:value="form.name" :placeholder="isAcmeIssue ? '可选，默认使用机构名与主域名' : ''" />
          </a-form-item>
          <a-form-item label="备注">
            <a-textarea v-model:value="form.remark" placeholder="可选" :auto-size="{ minRows: 1, maxRows: 6 }" />
          </a-form-item>
          <template v-if="isAcmeCert && !isAcmeIssue">
            <a-form-item label="证书机构">
              <a-input :value="acmeProviderLabel(form.acme_provider)" disabled />
            </a-form-item>
            <a-form-item label="自动更新">
              <a-switch v-model:checked="form.acme_auto_renew" />
              <p class="fs-hint is-inline">到期前 10 天起每日尝试续期；成功与失败都会通知所选通道。</p>
            </a-form-item>
          </template>
        </fs-form-section>

        <fs-form-section v-if="!isAcmeIssue" title="到期前通知" description="到期前 7 天每日会通知一次">
          <template #extra>
            <a-switch v-model:checked="form.expiry_notify_enabled" />
          </template>
          <a-form-item v-if="form.expiry_notify_enabled || form.acme_auto_renew" label="通知通道" required>
            <a-select v-model:value="form.expiry_notify_channel_ids" mode="multiple" placeholder="选择已配置的通知通道"
              allow-clear option-filter-prop="label" style="width: 100%">
              <a-select-option v-for="ch in channels" :key="ch.id" :value="ch.id" :label="ch.name"
                :disabled="!ch.enabled">
                {{ ch.name }}（{{ channelTypeLabel(ch.channel_type) }}）
              </a-select-option>
            </a-select>
            <p class="fs-hint is-inline">请先在「系统设置 → 通知通道」中配置邮件等通道。</p>
          </a-form-item>
        </fs-form-section>
      </template>

      <fs-form-section :title="isPanelImport ? undefined : '证书内容'"
        :description="contentSectionDescription">
        <a-tabs v-model:activeKey="importMode">
          <a-tab-pane key="paste" tab="粘贴内容">
            <a-form-item label="证书 (PEM)" required>
              <a-textarea v-model:value="form.cert_content" :rows="6" placeholder="-----BEGIN CERTIFICATE-----"
                class="fs-code-textarea" />
            </a-form-item>
            <a-form-item label="密钥 (KEY)" required>
              <a-textarea v-model:value="form.key_content" :rows="6" placeholder="-----BEGIN PRIVATE KEY-----"
                class="fs-code-textarea" />
            </a-form-item>
          </a-tab-pane>
          <a-tab-pane key="upload" tab="上传文件">
            <a-form-item label="证书文件 (.pem / .crt)" required>
              <a-upload :before-upload="onCertFile" :max-count="1" :file-list="certFileList" @remove="clearCertFile">
                <a-button>选择证书文件</a-button>
              </a-upload>
            </a-form-item>
            <a-form-item label="私钥文件 (.key / .pem)" required>
              <a-upload :before-upload="onKeyFile" :max-count="1" :file-list="keyFileList" @remove="clearKeyFile">
                <a-button>选择私钥文件</a-button>
              </a-upload>
            </a-form-item>
            <p v-if="certificateId" class="fs-hint">未选择新文件时，将保留当前证书内容。</p>
          </a-tab-pane>
          <a-tab-pane key="baota" tab="从宝塔导入">
            <panel-import-form v-if="importMode === 'baota'" ref="panelImportRef" kind="certificates" provider="baota"
              :replace-certificate-id="certificateId" @status="onPanelStatus" @imported="onPanelImported"
              @close="emit('update:open', false)" />
          </a-tab-pane>
          <a-tab-pane key="onepanel" tab="从 1Panel 导入">
            <panel-import-form v-if="importMode === 'onepanel'" ref="panelImportRef" kind="certificates"
              provider="onepanel" :replace-certificate-id="certificateId" @status="onPanelStatus"
              @imported="onPanelImported" @close="emit('update:open', false)" />
          </a-tab-pane>
          <a-tab-pane key="acme" tab="申请免费证书">
            <a-alert type="info" show-icon class="acme-alert"
              message="仅支持 HTTP-01。请确认所选域名的 A/AAAA 已指向本机，且公网可访问 80 端口（强制 HTTPS 的站点也会在 80 上回答挑战）。不支持通配符。" />
            <a-alert v-if="openedFromSite && !preselectSiteId" type="warning" show-icon class="acme-alert"
              message="请先保存站点后再申请免费证书。" />
            <a-form-item label="站点" required>
              <a-select v-model:value="acme.siteId" placeholder="选择已保存的站点" show-search option-filter-prop="label"
                style="width: 100%" :disabled="Boolean(openedFromSite && !preselectSiteId)"
                @change="onAcmeSiteChange">
                <a-select-option v-for="site in sites" :key="site.id" :value="site.id"
                  :label="site.name || site.domain">
                  {{ site.name || site.domain }}
                </a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="域名" required>
              <a-checkbox-group v-if="acmeSiteDomains.length" v-model:value="acme.domains" class="acme-domains">
                <a-checkbox v-for="domain in acmeSiteDomains" :key="domain" :value="domain">
                  {{ domain }}
                </a-checkbox>
              </a-checkbox-group>
              <p v-else class="fs-hint">请先选择站点。</p>
            </a-form-item>
            <a-form-item label="证书机构" required>
              <a-radio-group v-model:value="acme.provider">
                <a-radio value="letsencrypt">Let's Encrypt</a-radio>
                <a-radio value="zerossl">ZeroSSL</a-radio>
              </a-radio-group>
            </a-form-item>
            <a-form-item label="自动更新">
              <a-switch v-model:checked="acme.autoRenew" />
              <p class="fs-hint is-inline">到期前 10 天起每日尝试续期；请先在系统设置填写 ACME 账户邮箱。</p>
            </a-form-item>
            <a-form-item v-if="acme.autoRenew" label="通知通道" required>
              <a-select v-model:value="acme.channelIds" mode="multiple" placeholder="选择已配置的通知通道"
                allow-clear option-filter-prop="label" style="width: 100%">
                <a-select-option v-for="ch in channels" :key="ch.id" :value="ch.id" :label="ch.name"
                  :disabled="!ch.enabled">
                  {{ ch.name }}（{{ channelTypeLabel(ch.channel_type) }}）
                </a-select-option>
              </a-select>
              <p class="fs-hint is-inline">申请与续期的成功、失败都会发送到所选通道。</p>
            </a-form-item>
          </a-tab-pane>
        </a-tabs>
      </fs-form-section>
    </a-form>
  </fs-form-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { message, type UploadProps } from "ant-design-vue";
import { api } from "@/api";
import FsFormDrawer from "@/components/FsFormDrawer.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import PanelImportForm, { type PanelImportStatus } from "@/components/PanelImportForm.vue";
import type { SiteOption } from "@/composables/useSiteOptions";

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

interface CertificateBoundSite {
  id: number;
  name: string;
}

interface CertificateDetail {
  id: number;
  name: string;
  domains?: string | null;
  remark: string | null;
  cert_content: string;
  key_content: string;
  expiry_notify_enabled?: boolean;
  expiry_notify_channel_ids?: number[];
  acme_provider?: string | null;
  acme_auto_renew?: boolean;
  bound_sites?: CertificateBoundSite[];
}

const props = withDefaults(
  defineProps<{
    open: boolean;
    /** 传入时为更新模式，否则为导入/新建 */
    certificateId?: number | null;
    zIndex?: number;
    preselectSiteId?: number | null;
    openedFromSite?: boolean;
  }>(),
  {
    certificateId: null,
    zIndex: undefined,
    preselectSiteId: null,
    openedFromSite: false,
  },
);

const emit = defineEmits<{
  "update:open": [boolean];
  saved: [cert: CertificateSaved];
  imported: [];
}>();

const detailLoading = ref(false);
const saving = ref(false);
const importMode = ref<"paste" | "upload" | "baota" | "onepanel" | "acme">("paste");
const panelImportRef = ref<{ submit: () => Promise<void> } | null>(null);
const panelStatus = reactive<PanelImportStatus>({
  canImport: false,
  okText: "导入",
  importing: false,
  loading: false,
});
const channels = ref<NotificationChannelItem[]>([]);
const sites = ref<SiteOption[]>([]);

const isPanelImport = computed(
  () => importMode.value === "baota" || importMode.value === "onepanel",
);
const isAcmeIssue = computed(() => importMode.value === "acme");
const isAcmeCert = computed(() => Boolean(form.acme_provider));
const drawerOkText = computed(() => {
  if (isPanelImport.value) return panelStatus.okText;
  if (isAcmeIssue.value) return "申请证书";
  return undefined;
});
const contentSectionDescription = computed(() => {
  if (isPanelImport.value) return undefined;
  if (isAcmeIssue.value) return "通过 Let's Encrypt 或 ZeroSSL 签发并绑定站点";
  return "支持粘贴 PEM 文本或上传文件";
});

const form = reactive({
  name: "",
  remark: "",
  domains: "",
  cert_content: "",
  key_content: "",
  expiry_notify_enabled: false,
  expiry_notify_channel_ids: [] as number[],
  acme_provider: "" as string,
  acme_auto_renew: false,
  bound_sites: [] as CertificateBoundSite[],
});

const acme = reactive({
  siteId: null as number | null,
  domains: [] as string[],
  provider: "letsencrypt" as "letsencrypt" | "zerossl",
  autoRenew: true,
  channelIds: [] as number[],
});

const certFile = ref<File | null>(null);
const keyFile = ref<File | null>(null);
const certFileList = ref<UploadProps["fileList"]>([]);
const keyFileList = ref<UploadProps["fileList"]>([]);

const acmeSiteDomains = computed(() => {
  const site = sites.value.find((item) => item.id === acme.siteId);
  return site?.domains?.length ? site.domains : site?.domain ? [site.domain] : [];
});

function channelTypeLabel(type: string) {
  if (type === "email") return "邮件";
  if (type === "webhook") return "Webhook";
  if (type === "dingtalk") return "钉钉";
  if (type === "sms") return "短信";
  return type;
}

function acmeProviderLabel(provider: string | null | undefined) {
  if (provider === "letsencrypt") return "Let's Encrypt";
  if (provider === "zerossl") return "ZeroSSL";
  return provider || "手工导入";
}

function splitDomains(value: string | null | undefined) {
  return (value || "")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

function resetForm() {
  form.name = "";
  form.remark = "";
  form.domains = "";
  form.cert_content = "";
  form.key_content = "";
  form.expiry_notify_enabled = false;
  form.expiry_notify_channel_ids = [];
  form.acme_provider = "";
  form.acme_auto_renew = false;
  form.bound_sites = [];
  acme.siteId = null;
  acme.domains = [];
  acme.provider = "letsencrypt";
  acme.autoRenew = true;
  acme.channelIds = [];
  certFile.value = null;
  keyFile.value = null;
  certFileList.value = [];
  keyFileList.value = [];
  importMode.value = "paste";
}

function onAcmeSiteChange(id: number) {
  acme.siteId = id;
  const site = sites.value.find((item) => item.id === id);
  acme.domains = [...(site?.domains?.length ? site.domains : site?.domain ? [site.domain] : [])];
}

async function loadChannels() {
  try {
    const resp = await api.get<NotificationChannelItem[]>("/api/v1/notification-channels");
    channels.value = resp.data || [];
  } catch {
    channels.value = [];
  }
}

async function loadSites() {
  try {
    const resp = await api.get<SiteOption[]>("/api/v1/sites/options");
    sites.value = resp.data || [];
  } catch {
    sites.value = [];
  }
}

function initAcmeSelection() {
  if (props.preselectSiteId) {
    onAcmeSiteChange(props.preselectSiteId);
    return;
  }
  const certDomains = splitDomains(form.domains);
  if (certDomains.length) {
    const exact = sites.value.find((site) => {
      const have = new Set(site.domains?.length ? site.domains : site.domain ? [site.domain] : []);
      return certDomains.every((domain) => have.has(domain));
    });
    const overlap =
      exact ||
      sites.value.find((site) => {
        const have = new Set(site.domains?.length ? site.domains : site.domain ? [site.domain] : []);
        return certDomains.some((domain) => have.has(domain));
      });
    if (overlap) {
      acme.siteId = overlap.id;
      const have = overlap.domains?.length ? overlap.domains : overlap.domain ? [overlap.domain] : [];
      acme.domains = certDomains.filter((domain) => have.includes(domain));
      if (!acme.domains.length) acme.domains = [...have];
      return;
    }
  }
  if (form.bound_sites.length) {
    const boundId = form.bound_sites[0].id;
    if (sites.value.some((site) => site.id === boundId)) {
      onAcmeSiteChange(boundId);
    }
  }
}

async function loadDetail(id: number) {
  detailLoading.value = true;
  try {
    const resp = await api.get<CertificateDetail>(`/api/v1/certificates/${id}`);
    const detail = resp.data;
    form.name = detail.name;
    form.remark = detail.remark || "";
    form.domains = detail.domains || "";
    form.cert_content = detail.cert_content;
    form.key_content = detail.key_content;
    form.expiry_notify_enabled = Boolean(detail.expiry_notify_enabled);
    form.expiry_notify_channel_ids = [...(detail.expiry_notify_channel_ids || [])];
    form.acme_provider = detail.acme_provider || "";
    form.acme_auto_renew = Boolean(detail.acme_auto_renew);
    form.bound_sites = [...(detail.bound_sites || [])];
    acme.autoRenew = form.acme_auto_renew;
    acme.channelIds = [...form.expiry_notify_channel_ids];
    if (form.acme_provider === "zerossl" || form.acme_provider === "letsencrypt") {
      acme.provider = form.acme_provider;
    }
  } finally {
    detailLoading.value = false;
  }
}

watch(
  () => props.open,
  async (open) => {
    if (!open) return;
    resetForm();
    await Promise.all([loadChannels(), loadSites()]);
    if (props.certificateId) {
      await loadDetail(props.certificateId);
    }
    initAcmeSelection();
  },
);

watch(importMode, (mode) => {
  if (mode === "acme" && !acme.siteId) initAcmeSelection();
});

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
    expiry_notify_channel_ids: form.expiry_notify_enabled || form.acme_auto_renew
      ? [...form.expiry_notify_channel_ids]
      : [],
    acme_auto_renew: form.acme_auto_renew,
  };
}

function onPanelStatus(status: PanelImportStatus) {
  Object.assign(panelStatus, status);
}

function onPanelImported() {
  emit("update:open", false);
  emit("imported");
}

async function submitAcme() {
  if (props.openedFromSite && !props.preselectSiteId) {
    message.warning("请先保存站点后再申请免费证书");
    return;
  }
  if (!acme.siteId) {
    message.warning("请选择站点");
    return;
  }
  if (!acme.domains.length) {
    message.warning("请勾选至少一个域名");
    return;
  }
  if (acme.autoRenew && !acme.channelIds.length) {
    message.warning("开启自动更新时请选择通知通道");
    return;
  }
  saving.value = true;
  try {
    const resp = await api.post<CertificateSaved>(
      "/api/v1/certificates/acme/issue",
      {
        site_id: acme.siteId,
        domains: acme.domains,
        provider: acme.provider,
        auto_renew: acme.autoRenew,
        expiry_notify_channel_ids: acme.autoRenew ? [...acme.channelIds] : [],
        name: form.name.trim() || null,
        replace_certificate_id: props.certificateId || null,
      },
      { timeout: 120000 },
    );
    message.success("证书申请成功");
    emit("update:open", false);
    emit("saved", resp.data);
  } catch {
    // interceptor shows error
  } finally {
    saving.value = false;
  }
}

async function save() {
  if (isPanelImport.value) {
    await panelImportRef.value?.submit();
    return;
  }
  if (isAcmeIssue.value) {
    await submitAcme();
    return;
  }
  if (!form.name.trim()) {
    message.warning("请填写证书名称");
    return;
  }
  if (form.expiry_notify_enabled && !form.expiry_notify_channel_ids.length) {
    message.warning("启用到期前通知时请选择通知通道");
    return;
  }
  if (form.acme_auto_renew && !form.expiry_notify_channel_ids.length) {
    message.warning("开启自动更新时请选择通知通道");
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

<style scoped>
.acme-alert {
  margin-bottom: 16px;
}

.acme-domains {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
