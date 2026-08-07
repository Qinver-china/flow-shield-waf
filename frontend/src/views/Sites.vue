<template>
  <page-shell title="站点管理" description="配置防护域名、回源地址、HTTPS 证书与自定义拦截页">
    <template #actions>
      <a-button type="primary" @click="crudRef?.openCreate()">新增站点</a-button>
    </template>
    <resource-crud ref="crudRef" embedded title="站点管理" api-base="/api/v1/sites" :columns="columns" :filters="filters"
      :default-record="defaultRecord" :prepare-payload="preparePayload" :batch="batchConfig" name-field="name"
      detail-actions duplicatable @mutated="invalidateSiteOptions">
      <template
        #list="{ rows, loading, openView, openEdit, openDuplicate, remove, toggleEnabled, togglingId, allowDelete, nameActions, duplicatable: canDuplicate }">
        <a-spin :spinning="loading || (metricsLoading && !Object.keys(metricsMap).length)">
          <a-empty v-if="!rows.length" description="暂无站点，点击右上角新增" />
          <div v-else class="site-card-grid">
            <site-card v-for="site in rows" :key="site.id" :site="site" :metrics="metricsMap[String(site.id)]"
              :toggling="togglingId === site.id"
              :more-actions="cardMoreActions(site, { openEdit, openDuplicate, remove, allowDelete, canDuplicate, nameActions })"
              @view="openView(site)" @edit="openEdit(site)" @logs="goSiteLogs(site)"
              @toggle-enabled="(enabled) => toggleEnabled(site, enabled)" />
          </div>
        </a-spin>
      </template>

      <template #form="{ record, readonly, mode, enabledLoading, onEnabledPersist }">
        <div class="site-form">
          <fs-form-section title="域名配置">
            <template #extra>
              <form-enabled-switch v-model:checked="record.enabled" :immediate="mode === 'view'"
                :loading="enabledLoading" @immediate-change="onEnabledPersist" />
            </template>
            <a-row :gutter="16">
              <a-col :md="10" :lg="10" :xs="24">
                <a-form-item label="站点名称" required>
                  <a-input v-model:value="record.name" placeholder="例如：官网" :disabled="readonly" />
                </a-form-item>
              </a-col>
              <a-col :md="14" :lg="14" :xs="24">
                <a-form-item label="域名" required>
                  <a-select v-model:value="record.domains" mode="tags" :open="false" :token-separators="[',', ' ', ';']"
                    placeholder="输入域名后回车，支持输入多个域名，支持通配符" style="width: 100%" :disabled="readonly" />
                </a-form-item>
              </a-col>
            </a-row>
          </fs-form-section>
          <fs-form-section title="回源配置">
            <a-row :gutter="16">
              <a-col :md="12" :lg="12" :xs="18">
                <a-form-item label="源站地址" required>
                  <origin-host-input v-model:value="record.origin_host" :disabled="readonly" />
                </a-form-item>
              </a-col>
              <a-col :md="4" :lg="4" :xs="6">
                <a-form-item label="回源协议">
                  <a-select v-model:value="record.origin_protocol" :options="protocolOptions" :disabled="readonly" />
                </a-form-item>
              </a-col>
              <a-col :md="8" :lg="8" :xs="24">
                <a-form-item label="客户端 IP 获取方式">
                  <a-select v-model:value="record.client_ip_source" :disabled="readonly" style="width: 100%"
                    :options="clientIpSourceSelectOptions" />
                </a-form-item>
              </a-col>
              <a-col :span="24">
                <a-form-item label="回源端口">
                  <a-row :gutter="16">
                    <a-col :md="12" :lg="12" :xs="24">
                      <a-input-number v-model:value="record.origin_http_port" class="site-listen-port" :min="1"
                        :max="65535" :disabled="readonly" style="width: 100%">
                        <template #addonBefore>HTTP端口</template>
                        <template #addonAfter>
                          <div class="site-listen-addon">
                            <a-switch v-model:checked="record.listen_http" :disabled="readonly" />
                          </div>
                        </template>
                      </a-input-number>
                    </a-col>
                    <a-col :md="12" :lg="12" :xs="24">
                      <a-input-number v-model:value="record.origin_https_port" class="site-listen-port" :min="1"
                        :max="65535" :disabled="readonly" style="width: 100%">
                        <template #addonBefore>HTTPS端口</template>
                        <template #addonAfter>
                          <div class="site-listen-addon">
                            <a-switch v-model:checked="record.listen_https" :disabled="readonly" />
                          </div>
                        </template>
                      </a-input-number>
                    </a-col>
                  </a-row>
                </a-form-item>
                <template v-if="record.listen_https">
                  <a-form-item label="SSL 证书" required>
                    <template v-if="!readonly">
                      <div class="site-cert-combo">
                        <a-select v-model:value="record.certificate_id" class="site-cert-combo__select"
                          placeholder="请选择证书" :options="certSelectOptions"
                          :not-found-content="certOptions.length ? undefined : '暂无证书，请先导入'" allow-clear
                          @change="(v) => { if (!v) record.force_https = false }">
                          <template #dropdownRender="{ menuNode: menu }">
                            <div>
                              <site-cert-menu :vnodes="menu" />
                              <a-divider style="margin: 4px 0" />
                              <div class="site-cert-dropdown-action" @mousedown.prevent>
                                <a-button type="link" block @click="openImportCert(record)">
                                  <template #icon><plus-outlined /></template>
                                  添加新的证书
                                </a-button>
                              </div>
                            </div>
                          </template>
                        </a-select>
                        <div class="site-cert-combo__addon">
                          <span>强制 HTTPS</span>
                          <a-switch v-model:checked="record.force_https" :disabled="!record.certificate_id" />
                        </div>
                      </div>
                    </template>
                    <div v-else class="site-cert-combo"
                      :class="{ 'site-cert-combo--with-addon': !!record.certificate_id }">
                      <span class="site-cert-combo__readonly">{{ certName(record.certificate_id) }}</span>
                      <div class="site-cert-combo__addon">
                        <span>强制 HTTPS</span>
                        <a-switch v-model:checked="record.force_https" :disabled="readonly || !record.certificate_id" />
                      </div>
                    </div>
                  </a-form-item>
                </template>
              </a-col>
            </a-row>

          </fs-form-section>
          <fs-form-section title="高级配置">
            <div class="fs-switch-row">
              <div>
                <div><b>关闭内容缓冲</b></div>
                <div>如果源站在本机，建议开启此开关</div>
              </div>
              <a-switch v-model:checked="record.disable_content_buffering" :disabled="readonly" />
            </div>
            <div class="fs-switch-row">
              <div>
                <div><b>自定义拦截页面</b></div>
                <div>为此站点自定义拦截页面内容，优先级低于规则/黑名单/限速的专属配置</div>
              </div>
              <a-switch v-model:checked="record.custom_block_page_enabled" :disabled="readonly" />
            </div>
            <template v-if="record.custom_block_page_enabled">
              <a-form-item label="响应状态码">
                <a-select v-model:value="record.block_page_status_code" :disabled="readonly"
                  :options="blockStatusOptions" />
              </a-form-item>
              <a-form-item label="HTML 内容">
                <a-textarea v-model:value="record.block_page_html" :rows="10" :disabled="readonly"
                  class="fs-code-textarea" />
              </a-form-item>
            </template>
            <div class="fs-switch-row">
              <div>
                <div><b>自定义人机验证页脚</b></div>
                <div>为此站点自定义人机验证页面的底部页脚显示内容，优先级低于规则/黑名单/限速的专属配置</div>
              </div>
              <a-switch v-model:checked="record.custom_captcha_footer_enabled" :disabled="readonly" />
            </div>
            <template v-if="record.custom_captcha_footer_enabled">
              <a-form-item label="页脚 HTML">
                <a-textarea v-model:value="record.captcha_footer_html" :rows="4" :disabled="readonly"
                  class="fs-code-textarea" />
              </a-form-item>
            </template>
          </fs-form-section>
        </div>
      </template>
    </resource-crud>

    <certificate-form-drawer v-model:open="certDrawerOpen" :z-index="1100" @saved="onCertImported" />
  </page-shell>
</template>

<script setup lang="ts">
import { computed, defineComponent, onMounted, onUnmounted, reactive, ref } from "vue";
import { PlusOutlined } from "@ant-design/icons-vue";
import PageShell from "@/components/PageShell.vue";
import ResourceCrud from "@/components/ResourceCrud.vue";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import OriginHostInput from "@/components/OriginHostInput.vue";
import CertificateFormDrawer, { type CertificateSaved } from "@/components/CertificateFormDrawer.vue";
import SiteCard, { type SiteCardMetrics } from "@/components/SiteCard.vue";
import { enabledFilterOptions } from "@/constants/resourceList";
import { commonBatchEditFields } from "@/constants/batch";
import { CLIENT_IP_SOURCE_OPTIONS } from "@/constants/clientIpSource";
import { useLogNavigation } from "@/composables/useLogNavigation";
import { invalidateSiteOptions } from "@/composables/useSiteOptions";
import type { ResourceQuickAction } from "@/composables/useResourceQuickActions";
import { api } from "@/api";
import type { BatchConfig } from "@/types/batch";
import type { ResourceColumn, ResourceFilterField } from "@/types/resourceList";

/** Render Select dropdown menu VNode inside custom dropdownRender. */
const SiteCertMenu = defineComponent({
  name: "SiteCertMenu",
  props: {
    vnodes: { type: Object, required: true },
  },
  setup(props) {
    return () => props.vnodes as any;
  },
});

interface CertOption {
  id: number;
  name: string;
  domains: string | null;
  not_after: string | null;
}

const { goToLogs } = useLogNavigation();
const crudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);
const certOptions = ref<CertOption[]>([]);
const certDrawerOpen = ref(false);
const certSelectRecord = ref<Record<string, any> | null>(null);
const metricsLoading = ref(false);
const metricsMap = reactive<Record<string, SiteCardMetrics>>({});
let metricsTimer: ReturnType<typeof setInterval> | null = null;

const protocolOptions = [
  { value: "follow", label: "跟随协议" },
  { value: "http", label: "HTTP" },
  { value: "https", label: "HTTPS" },
];

const clientIpSourceSelectOptions = CLIENT_IP_SOURCE_OPTIONS.map((o) => ({
  value: o.value,
  label: o.label,
}));

const blockStatusOptions = [
  { value: 403, label: "403 Forbidden" },
  { value: 429, label: "429 Too Many Requests" },
  { value: 451, label: "451 Unavailable For Legal Reasons" },
  { value: 503, label: "503 Service Unavailable" },
];

const filters: ResourceFilterField[] = [
  { key: "q", label: "搜索", type: "search", placeholder: "名称 / 域名 / 源站" },
  { key: "enabled", label: "状态", type: "select", options: enabledFilterOptions },
];

const batchConfig: BatchConfig = {
  editFields: [commonBatchEditFields.enabled],
};

const columns: ResourceColumn[] = [
  { title: "名称", dataIndex: "name", sorter: true },
  { title: "域名", dataIndex: "domains_display", sorter: true },
  { title: "源站", dataIndex: "origin_display" },
  { title: "状态", key: "enabled", dataIndex: "enabled", width: 90, sorter: true },
];

const certSelectOptions = computed(() =>
  certOptions.value.map((c) => ({
    value: c.id,
    label: c.domains ? `${c.name}（${c.domains}）` : c.name,
  })),
);

const defaultRecord = () => ({
  name: "",
  domains: [] as string[],
  origin_host: "",
  origin_protocol: "follow",
  origin_http_port: 80,
  origin_https_port: 443,
  client_ip_source: "remote_addr",
  listen_http: true,
  listen_https: false,
  force_https: false,
  disable_content_buffering: false,
  certificate_id: null as number | null,
  enabled: true,
  custom_block_page_enabled: false,
  block_page_status_code: 403,
  block_page_html: "",
  custom_captcha_footer_enabled: false,
  captcha_footer_html: "",
});

function preparePayload(row: Record<string, any>) {
  const domains = Array.isArray(row.domains)
    ? row.domains.map((item: string) => String(item).trim().toLowerCase()).filter(Boolean)
    : [];
  if (!domains.length) {
    throw new Error("至少输入一个域名");
  }
  row.domains = [...new Set(domains)];
  if (!row.listen_http && !row.listen_https) {
    throw new Error("至少需要开启 HTTP 或 HTTPS 监听");
  }
  if (row.listen_https && !row.certificate_id) {
    throw new Error("开启 HTTPS 时必须选择 SSL 证书");
  }
  if (row.force_https && (!row.listen_https || !row.certificate_id)) {
    throw new Error("开启强制 HTTPS 需要先开启 HTTPS 监听并选择 SSL 证书");
  }
  if (!row.listen_https || !row.certificate_id) {
    row.force_https = false;
  }
  if (row.custom_block_page_enabled && !(row.block_page_html || "").trim()) {
    throw new Error("启用自定义拦截页时必须填写 HTML 内容");
  }
  if (row.custom_captcha_footer_enabled && !(row.captcha_footer_html || "").trim()) {
    throw new Error("启用自定义人机验证页脚时必须填写 HTML 内容");
  }
  return row;
}

async function loadCertOptions() {
  const resp = await api.get<CertOption[]>("/api/v1/certificates/options");
  certOptions.value = resp.data;
}

function openImportCert(record: Record<string, any>) {
  certSelectRecord.value = record;
  certDrawerOpen.value = true;
}

async function onCertImported(cert: CertificateSaved) {
  await loadCertOptions();
  const target = certSelectRecord.value;
  if (target) {
    target.certificate_id = cert.id;
  }
}

async function loadMetrics() {
  metricsLoading.value = true;
  try {
    const resp = await api.get<{ items: Record<string, SiteCardMetrics> }>("/api/v1/sites/metrics");
    const items = resp.data.items || {};
    for (const key of Object.keys(metricsMap)) {
      if (!(key in items)) delete metricsMap[key];
    }
    Object.assign(metricsMap, items);
  } catch {
    // 指标失败不影响站点列表本身
  } finally {
    metricsLoading.value = false;
  }
}

function certName(id: number | null) {
  if (!id) return "-";
  const cert = certOptions.value.find((c) => c.id === id);
  return cert ? (cert.domains ? `${cert.name}（${cert.domains}）` : cert.name) : `#${id}`;
}

function goSiteLogs(site: Record<string, any>) {
  goToLogs({ tab: "detail", preset: "24h", site_id: Number(site.id) });
}

function cardMoreActions(
  site: Record<string, any>,
  ctx: {
    openEdit: (row: any) => void;
    openDuplicate: (row: any) => void;
    remove: (id: number) => void;
    allowDelete: (row: any) => boolean;
    canDuplicate: boolean;
    nameActions: (row: any) => ResourceQuickAction[];
  },
) {
  const actions = ctx.nameActions(site).filter(
    (a) => a.key !== "edit" && a.key !== "logs-hit" && a.key !== "logs-stats",
  );
  if (!actions.length && ctx.canDuplicate) {
    actions.push({
      key: "duplicate",
      label: "复制",
      onClick: () => ctx.openDuplicate(site),
    });
  }
  if (ctx.allowDelete(site) && !actions.some((a) => a.key === "delete")) {
    actions.push({
      key: "delete",
      label: "删除",
      danger: true,
      divided: true,
      confirm: "确认删除该站点？",
      onClick: () => ctx.remove(site.id),
    });
  }
  return actions;
}

onMounted(() => {
  void loadCertOptions();
  void loadMetrics();
  metricsTimer = setInterval(() => {
    void loadMetrics();
  }, 30_000);
});

onUnmounted(() => {
  if (metricsTimer) clearInterval(metricsTimer);
});
</script>

<style scoped>
.site-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.site-listen-addon {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.site-listen-port :deep(.ant-input-number-group-addon) {
  padding-inline: 11px;
}

.site-cert-combo {
  display: flex;
  width: 100%;
  align-items: stretch;
}

.site-cert-combo__select {
  flex: 1;
  min-width: 0;
}

.site-cert-combo__select :deep(.ant-select-selector) {
  border-start-end-radius: 0;
  border-end-end-radius: 0;
}

.site-cert-combo__readonly {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  padding: 4px 11px;
  border: 1px solid var(--fs-border);
  border-radius: var(--fs-radius-sm);
  background: var(--fs-bg-muted);
  color: var(--fs-text-secondary);
  line-height: 1.5715;
}

.site-cert-combo--with-addon .site-cert-combo__readonly {
  border-start-end-radius: 0;
  border-end-end-radius: 0;
  border-inline-end: 0;
}

.site-cert-combo__addon {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding: 0 11px;
  border: 1px solid var(--fs-border, #d9d9d9);
  border-inline-start: 0;
  border-radius: 0 var(--fs-radius-sm, 6px) var(--fs-radius-sm, 6px) 0;
  background: var(--fs-bg-muted, rgba(0, 0, 0, 0.02));
  white-space: nowrap;
  font-size: 13px;
  color: var(--fs-text-secondary, rgba(0, 0, 0, 0.65));
}

.site-cert-dropdown-action {
  padding: 4px 8px;
}

@media (max-width: 767px) {
  .site-card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
