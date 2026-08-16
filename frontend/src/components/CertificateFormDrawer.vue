<template>
  <fs-form-drawer :open="open" title="SSL 证书" :subtitle="certificateId ? `#${certificateId}` : undefined"
    :mode="certificateId ? 'edit' : 'create'" :width="760" :z-index="zIndex"
    :loading="isPanelImport ? panelStatus.loading : detailLoading"
    :confirm-loading="isPanelImport ? panelStatus.importing : saving" :ok-text="drawerOkText"
    :hide-ok="isPanelImport ? !panelStatus.canImport : false" @update:open="emit('update:open', $event)" @ok="save">
    <a-form layout="vertical">
      <template v-if="!isPanelImport">
        <fs-form-section title="基本信息">
          <a-row :gutter="16">
            <a-col :xs="24" :md="10">
              <a-form-item label="证书名称" :required="!isAcmeIssue">
                <a-input v-model:value="form.name" :placeholder="isAcmeIssue ? '可选，默认使用机构名与主域名' : ''" />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :md="14">
              <a-form-item label="备注">
                <a-textarea v-model:value="form.remark" placeholder="可选" :auto-size="{ minRows: 1, maxRows: 6 }" />
              </a-form-item>
            </a-col>
          </a-row>
        </fs-form-section>
      </template>
      <fs-form-section :title="isPanelImport ? undefined : '证书内容'">
        <a-tabs v-model:activeKey="importMode">
          <a-tab-pane key="paste" tab="粘贴内容">
            <a-row :gutter="16">
              <a-col :xs="24" :md="12">
                <a-form-item label="证书 (PEM)" required>
                  <a-textarea v-model:value="form.cert_content" :rows="6" placeholder="-----BEGIN CERTIFICATE-----"
                    class="fs-code-textarea" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="12">
                <a-form-item label="密钥 (KEY)" required>
                  <a-textarea v-model:value="form.key_content" :rows="6" placeholder="-----BEGIN PRIVATE KEY-----"
                    class="fs-code-textarea" />
                </a-form-item>
              </a-col>
            </a-row>

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
          <a-tab-pane key="acme" tab="申请免费证书">
            <a-alert v-if="openedFromSite && !preselectSiteId" type="warning" show-icon class="acme-alert"
              message="请先保存站点后再申请免费证书。" />
            <a-form-item label="站点" required>
              <a-select v-model:value="acme.siteId" placeholder="选择已保存的站点" show-search option-filter-prop="label"
                style="width: 100%" :disabled="acmeBusy || Boolean(openedFromSite && !preselectSiteId)"
                @change="onAcmeSiteChange">
                <a-select-option v-for="site in sites" :key="site.id" :value="site.id"
                  :label="site.name || site.domain">
                  {{ site.name || site.domain }}
                </a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="域名" required>
              <a-checkbox-group v-if="acmeSiteDomains.length" v-model:value="acme.domains" class="acme-domains"
                :disabled="acmeBusy">
                <a-checkbox v-for="domain in acmeSiteDomains" :key="domain" :value="domain">
                  {{ domain }}
                </a-checkbox>
              </a-checkbox-group>
              <p v-else class="fs-hint">请先选择站点。</p>
            </a-form-item>
            <a-form-item label="证书机构" required>
              <a-radio-group v-model:value="acmeProviderModel" :disabled="acmeBusy">
                <a-radio value="letsencrypt">Let's Encrypt(推荐)</a-radio>
                <a-radio value="zerossl">ZeroSSL</a-radio>
              </a-radio-group>
            </a-form-item>
            <div v-if="acmeLogs.length || acmeError" class="acme-log-panel">
              <div class="acme-log-panel__title">申请进度</div>
              <div ref="acmeLogEl" class="acme-log-panel__body">
                <div v-for="(line, idx) in acmeLogs" :key="idx" class="acme-log-line"
                  :class="{ 'is-error': line.level === 'error', 'is-ok': line.level === 'ok' }">
                  <span class="acme-log-time">{{ line.time }}</span>
                  <span>{{ line.message }}</span>
                </div>
              </div>
              <a-alert v-if="acmeError" type="error" show-icon class="acme-alert" :message="acmeError" />
            </div>
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
        </a-tabs>
      </fs-form-section>

      <template v-if="!isPanelImport">
        <fs-form-section title="高级功能">
          <div class="fs-switch-row">
            <div class="fs-switch-row-header">
              <div>
                <div><b>到期前通知</b></div>
                <div class="fs-muted">到期前7天，每日会通知一次</div>
              </div>
              <a-switch v-model:checked="form.expiry_notify_enabled" />
            </div>
            <div class="fs-switch-row-body" v-if="form.expiry_notify_enabled">
              <a-form-item label="通知通道" required>
                <a-select v-model:value="form.expiry_notify_channel_ids" mode="multiple" placeholder="选择已配置的通知通道"
                  allow-clear option-filter-prop="label" style="width: 100%">
                  <a-select-option v-for="ch in channels" :key="ch.id" :value="ch.id" :label="ch.name"
                    :disabled="!ch.enabled">
                    {{ ch.name }}（{{ channelTypeLabel(ch.channel_type) }}）
                  </a-select-option>
                </a-select>
              </a-form-item>
            </div>
          </div>
          <div class="fs-switch-row">
            <div class="fs-switch-row-header">
              <div>
                <div><b>到期前自动续期</b></div>
                <div class="fs-muted">到期前10天起，每日将尝试自动申请免费证书续期</div>
              </div>
              <a-switch v-model:checked="form.acme_auto_renew" />
            </div>
            <div class="fs-switch-row-body" v-if="form.acme_auto_renew">
              <a-form-item label="证书机构" required>
                <a-radio-group v-model:value="acmeProviderModel">
                  <a-radio value="letsencrypt">Let's Encrypt(推荐)</a-radio>
                  <a-radio value="zerossl">ZeroSSL</a-radio>
                </a-radio-group>
              </a-form-item>
              <a-form-item label="绑定站点" required>
                <a-select v-model:value="renew.siteId" placeholder="选择已保存的站点" show-search option-filter-prop="label"
                  style="width: 100%" @change="onRenewSiteChange">
                  <a-select-option v-for="site in sites" :key="site.id" :value="site.id"
                    :label="site.name || site.domain">
                    {{ site.name || site.domain }}
                  </a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="续期域名" required>
                <a-checkbox-group v-if="renewSiteDomains.length" v-model:value="renew.domains" class="acme-domains">
                  <a-checkbox v-for="domain in renewSiteDomains" :key="domain" :value="domain">
                    {{ domain }}
                  </a-checkbox>
                </a-checkbox-group>
                <p v-else class="fs-hint">请先选择站点。</p>
              </a-form-item>
              <a-form-item label="通知通道" required>
                <a-select v-model:value="form.expiry_notify_channel_ids" mode="multiple" placeholder="选择自动续签的结果通知通道"
                  allow-clear option-filter-prop="label" style="width: 100%">
                  <a-select-option v-for="ch in channels" :key="ch.id" :value="ch.id" :label="ch.name"
                    :disabled="!ch.enabled">
                    {{ ch.name }}（{{ channelTypeLabel(ch.channel_type) }}）
                  </a-select-option>
                </a-select>
              </a-form-item>
            </div>
          </div>
        </fs-form-section>
      </template>

    </a-form>
  </fs-form-drawer>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from "vue";
import { message, type UploadProps } from "ant-design-vue";
import { api } from "@/api";
import FsFormDrawer from "@/components/FsFormDrawer.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import PanelImportForm, { type PanelImportStatus } from "@/components/PanelImportForm.vue";
import type { SiteOption } from "@/composables/useSiteOptions";
import { useAppSettingsStore } from "@/stores/appSettings";

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
const appSettings = useAppSettingsStore();

interface AcmeLogLine {
  time: string;
  message: string;
  level: "info" | "error" | "ok";
}

const acmeLogs = ref<AcmeLogLine[]>([]);
const acmeError = ref("");
const acmeLogEl = ref<HTMLElement | null>(null);
const acmeBusy = computed(() => saving.value && importMode.value === "acme");

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

const isPanelImport = computed(
  () => importMode.value === "baota" || importMode.value === "onepanel",
);
const isAcmeIssue = computed(() => importMode.value === "acme");
const drawerOkText = computed(() => {
  if (isPanelImport.value) return panelStatus.okText;
  if (isAcmeIssue.value) return "立即申请";
  return undefined;
});

const acmeProviderModel = computed({
  get: () => (form.acme_provider === "zerossl" ? "zerossl" : "letsencrypt"),
  set: (value: "letsencrypt" | "zerossl") => {
    form.acme_provider = value;
  },
});

const acme = reactive({
  siteId: null as number | null,
  domains: [] as string[],
});

const renew = reactive({
  siteId: null as number | null,
  domains: [] as string[],
});

const certFile = ref<File | null>(null);
const keyFile = ref<File | null>(null);
const certFileList = ref<UploadProps["fileList"]>([]);
const keyFileList = ref<UploadProps["fileList"]>([]);

function siteDomainList(site: SiteOption | undefined) {
  if (!site) return [] as string[];
  return site.domains?.length ? site.domains : site.domain ? [site.domain] : [];
}

const acmeSiteDomains = computed(() => siteDomainList(sites.value.find((item) => item.id === acme.siteId)));
const renewSiteDomains = computed(() => siteDomainList(sites.value.find((item) => item.id === renew.siteId)));

function channelTypeLabel(type: string) {
  if (type === "email") return "邮件";
  if (type === "webhook") return "Webhook";
  if (type === "dingtalk") return "钉钉";
  if (type === "sms") return "短信";
  return type;
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
  form.acme_provider = "letsencrypt";
  form.acme_auto_renew = false;
  form.bound_sites = [];
  acme.siteId = null;
  acme.domains = [];
  renew.siteId = null;
  renew.domains = [];
  acmeLogs.value = [];
  acmeError.value = "";
  certFile.value = null;
  keyFile.value = null;
  certFileList.value = [];
  keyFileList.value = [];
  importMode.value = "paste";
}

function onAcmeSiteChange(id: number) {
  acme.siteId = id;
  acme.domains = [...siteDomainList(sites.value.find((item) => item.id === id))];
}

function onRenewSiteChange(id: number) {
  renew.siteId = id;
  renew.domains = [...siteDomainList(sites.value.find((item) => item.id === id))];
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

function pickSiteForDomains(certDomains: string[]) {
  if (!certDomains.length) return null;
  const exact = sites.value.find((site) => {
    const have = new Set(siteDomainList(site));
    return certDomains.every((domain) => have.has(domain));
  });
  const overlap =
    exact ||
    sites.value.find((site) => {
      const have = new Set(siteDomainList(site));
      return certDomains.some((domain) => have.has(domain));
    });
  if (!overlap) return null;
  const have = siteDomainList(overlap);
  const selected = certDomains.filter((domain) => have.includes(domain));
  return {
    siteId: overlap.id,
    domains: selected.length ? selected : [...have],
  };
}

function initDomainSelections() {
  if (props.preselectSiteId) {
    onAcmeSiteChange(props.preselectSiteId);
    onRenewSiteChange(props.preselectSiteId);
    return;
  }

  const certDomains = splitDomains(form.domains);
  const matched = pickSiteForDomains(certDomains);
  if (matched) {
    acme.siteId = matched.siteId;
    acme.domains = [...matched.domains];
    renew.siteId = matched.siteId;
    renew.domains = [...matched.domains];
    return;
  }

  if (form.bound_sites.length) {
    const boundId = form.bound_sites[0].id;
    if (sites.value.some((site) => site.id === boundId)) {
      onAcmeSiteChange(boundId);
      onRenewSiteChange(boundId);
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
    form.acme_provider =
      detail.acme_provider === "zerossl" || detail.acme_provider === "letsencrypt"
        ? detail.acme_provider
        : "letsencrypt";
    form.acme_auto_renew = Boolean(detail.acme_auto_renew);
    form.bound_sites = [...(detail.bound_sites || [])];
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
    initDomainSelections();
  },
);

watch(importMode, (mode) => {
  if (mode === "acme" && !acme.siteId) initDomainSelections();
});

watch(
  () => form.acme_auto_renew,
  (enabled) => {
    if (!enabled) return;
    if (!renew.siteId) initDomainSelections();
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

function validateAutoRenewSettings(): boolean {
  if (!form.acme_auto_renew) return true;
  if (!renew.domains.length) {
    message.warning("开启自动续期时请勾选至少一个域名");
    return false;
  }
  if (!form.expiry_notify_channel_ids.length) {
    message.warning("开启自动续期时请选择通知通道");
    return false;
  }
  return true;
}

function notifyPayload() {
  const channelsNeeded = form.expiry_notify_enabled || form.acme_auto_renew;
  const payload: Record<string, unknown> = {
    expiry_notify_enabled: form.expiry_notify_enabled,
    expiry_notify_channel_ids: channelsNeeded ? [...form.expiry_notify_channel_ids] : [],
    acme_auto_renew: form.acme_auto_renew,
  };
  if (form.acme_auto_renew) {
    payload.acme_provider = acmeProviderModel.value;
    payload.renew_domains = [...renew.domains];
  }
  return payload;
}

function onPanelStatus(status: PanelImportStatus) {
  Object.assign(panelStatus, status);
}

function onPanelImported() {
  emit("update:open", false);
  emit("imported");
}

function formatAcmeLogTime() {
  const now = new Date();
  return [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");
}

async function appendAcmeLog(messageText: string, level: AcmeLogLine["level"] = "info") {
  acmeLogs.value.push({
    time: formatAcmeLogTime(),
    message: messageText,
    level,
  });
  await nextTick();
  if (acmeLogEl.value) {
    acmeLogEl.value.scrollTop = acmeLogEl.value.scrollHeight;
  }
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
  if (form.expiry_notify_enabled && !form.expiry_notify_channel_ids.length) {
    message.warning("启用到期前通知时请选择通知通道");
    return;
  }
  if (!validateAutoRenewSettings()) return;
  if (!appSettings.loaded) {
    try {
      await appSettings.fetch();
    } catch {
      // ignore; backend will validate
    }
  }
  if (!appSettings.acmeAccountEmail?.trim()) {
    message.warning("请先在「系统设置 → 显示设置」填写 ACME 账户邮箱");
    return;
  }

  // Editing: persist notify/renew settings first so they survive even if issue fails later.
  if (props.certificateId) {
    try {
      await api.put(`/api/v1/certificates/${props.certificateId}`, notifyPayload());
    } catch {
      return;
    }
  }

  acmeLogs.value = [];
  acmeError.value = "";
  saving.value = true;
  try {
    await appendAcmeLog("开始申请免费证书…");
    const token = localStorage.getItem("waf_access_token");
    const resp = await fetch("/api/v1/certificates/acme/issue/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        site_id: acme.siteId,
        domains: acme.domains,
        provider: acmeProviderModel.value,
        auto_renew: form.acme_auto_renew,
        expiry_notify_enabled: form.expiry_notify_enabled,
        expiry_notify_channel_ids:
          form.acme_auto_renew || form.expiry_notify_enabled
            ? [...form.expiry_notify_channel_ids]
            : [],
        renew_domains: form.acme_auto_renew ? [...renew.domains] : null,
        name: form.name.trim() || null,
        replace_certificate_id: props.certificateId || null,
      }),
    });

    if (!resp.ok) {
      if (resp.status === 401) {
        localStorage.removeItem("waf_access_token");
        location.href = "/login";
        return;
      }
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.message || err.detail || "申请失败");
    }

    const reader = resp.body?.getReader();
    if (!reader) throw new Error("无法读取申请进度");

    const decoder = new TextDecoder();
    let buffer = "";
    let finished = false;
    let saved: CertificateSaved | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") {
          finished = true;
          continue;
        }
        let parsed: Record<string, unknown>;
        try {
          parsed = JSON.parse(raw);
        } catch {
          continue;
        }
        if (parsed.type === "log") {
          await appendAcmeLog(String(parsed.message || ""));
        } else if (parsed.type === "error") {
          const errText = String(parsed.message || "申请失败");
          acmeError.value = errText;
          await appendAcmeLog(errText, "error");
          finished = true;
        } else if (parsed.type === "done") {
          saved = (parsed.data || null) as CertificateSaved | null;
          await appendAcmeLog("证书申请成功", "ok");
          finished = true;
        }
      }
    }

    if (acmeError.value) {
      message.error(acmeError.value);
      return;
    }
    if (!finished || !saved) {
      throw new Error("连接中断，证书申请未完成");
    }
    message.success("证书申请成功");
    emit("update:open", false);
    emit("saved", saved);
  } catch (e: unknown) {
    const errText = e instanceof Error ? e.message : "申请失败";
    acmeError.value = errText;
    await appendAcmeLog(errText, "error");
    message.error(errText);
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
  if (!validateAutoRenewSettings()) return;

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
      if ((notify.expiry_notify_channel_ids as number[]).length) {
        fd.append("expiry_notify_channel_ids", JSON.stringify(notify.expiry_notify_channel_ids));
      }
      fd.append("acme_auto_renew", String(notify.acme_auto_renew));
      if (notify.acme_auto_renew) {
        fd.append("acme_provider", String(notify.acme_provider));
        fd.append("renew_domains", JSON.stringify(notify.renew_domains));
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
  margin: 4px 12px 8px;
}

.acme-log-panel {
  margin-top: 8px;
  border: 1px solid var(--fs-border, #e2e8f0);
  border-radius: 8px;
  overflow: hidden;
  background: var(--fs-bg-elevated);
}

.acme-log-panel__title {
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  border-bottom: 1px solid var(--fs-border, #e2e8f0);
}

.acme-log-panel__body {
  max-height: 220px;
  overflow: auto;
  padding: 8px 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
  background: var(--fs-bg-muted, #f8fafc);
}

.acme-log-line {
  display: flex;
  gap: 8px;
}

.acme-log-line.is-error {
  color: var(--fs-danger, #dc2626);
}

.acme-log-line.is-ok {
  color: var(--fs-success, #16a34a);
}

.acme-log-time {
  flex: none;
  color: var(--fs-text-muted, #64748b);
}
</style>
