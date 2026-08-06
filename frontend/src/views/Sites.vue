<template>
  <page-shell title="站点管理" description="配置防护域名、回源地址、HTTPS 证书与自定义拦截页">
    <template #actions>
      <a-button type="primary" @click="crudRef?.openCreate()">新增站点</a-button>
    </template>
    <resource-crud
    ref="crudRef"
    embedded
    title="站点管理"
    api-base="/api/v1/sites"
    :columns="columns"
    :filters="filters"
    :default-record="defaultRecord"
    :prepare-payload="preparePayload"
    :batch="batchConfig"
    name-field="name"
    detail-actions
    duplicatable
  >
    <template #list="{ rows, loading, openView, openEdit, openDuplicate, remove, toggleEnabled, togglingId, allowDelete, nameActions, duplicatable: canDuplicate }">
      <a-spin :spinning="loading || (metricsLoading && !Object.keys(metricsMap).length)">
        <a-empty v-if="!rows.length" description="暂无站点，点击右上角新增" />
        <div v-else class="site-card-grid">
          <site-card
            v-for="site in rows"
            :key="site.id"
            :site="site"
            :metrics="metricsMap[String(site.id)]"
            :toggling="togglingId === site.id"
            :more-actions="cardMoreActions(site, { openEdit, openDuplicate, remove, allowDelete, canDuplicate, nameActions })"
            @view="openView(site)"
            @edit="openEdit(site)"
            @logs="goSiteLogs(site)"
            @toggle-enabled="(enabled) => toggleEnabled(site, enabled)"
          />
        </div>
      </a-spin>
    </template>

    <template #form="{ record, readonly, mode, enabledLoading, onEnabledPersist }">
      <div class="site-form">
        <fs-form-section title="域名配置">
          <template #extra>
            <form-enabled-switch
              v-model:checked="record.enabled"
              :immediate="mode === 'view'"
              :loading="enabledLoading"
              @immediate-change="onEnabledPersist"
            />
          </template>
          <a-alert
            v-if="!record.enabled"
            type="warning"
            show-icon
            style="margin-bottom: 16px"
            message="禁用站点将从引擎移除 Nginx 配置，该域名将无法访问（并非仅关闭 WAF 检测）。"
          />
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="站点名称" required>
                <a-input v-model:value="record.name" placeholder="例如：官网" :disabled="readonly" />
              </a-form-item>
            </a-col>
            <a-col :span="24">
              <a-form-item label="域名" required extra="可输入多个域名，回车或逗号分隔，例如 www.example.com 与 example.com">
                <a-select
                  v-model:value="record.domains"
                  mode="tags"
                  :token-separators="[',', ' ', ';']"
                  placeholder="输入域名后回车"
                  style="width: 100%"
                  :disabled="readonly"
                  :options="[]"
                />
              </a-form-item>
            </a-col>
          </a-row>
        </fs-form-section>

        <fs-form-section title="回源配置" description="配置 WAF 到源站的转发地址与协议">
          <a-row :gutter="16">
            <a-col :span="14">
              <a-form-item label="源站" required extra="合法域名或 IP，无需 https:// 前缀">
                <origin-host-input v-model:value="record.origin_host" :disabled="readonly" />
              </a-form-item>
            </a-col>
            <a-col :span="10">
              <a-form-item label="回源协议">
                <a-select v-model:value="record.origin_protocol" :options="protocolOptions" :disabled="readonly" />
              </a-form-item>
            </a-col>
            <a-col :span="14">
              <a-form-item
                label="客户端 IP 获取方式"
                :extra="clientIpSourceExtra(record.client_ip_source)"
              >
                <a-select
                  v-model:value="record.client_ip_source"
                  :disabled="readonly"
                  style="width: 100%"
                  :options="clientIpSourceSelectOptions"
                />
              </a-form-item>
              <a-alert
                v-if="record.client_ip_source && record.client_ip_source !== 'remote_addr'"
                type="warning"
                show-icon
                style="margin-bottom: 16px"
                message="非直连 IP 模式将信任请求头中的客户端地址"
                description="请确保仅可信 CDN / 反代能直连本引擎；若攻击者可直连并伪造 IP 头，黑白名单、限速与挑战放行均可被绕过或嫁祸。生产环境务必在上游网络层限制来源。"
              />
            </a-col>
            <a-col :span="10">
              <a-form-item
                label="关闭内容缓冲"
                extra="如果源站在本机，建议开启此开关"
              >
                <a-switch v-model:checked="record.disable_content_buffering" :disabled="readonly" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16" style="margin-bottom: 12px;">
            <a-col :span="12">
              <a-form-item label="HTTP 端口">
                <a-input-number
                  v-model:value="record.origin_http_port"
                  :min="1"
                  :max="65535"
                  style="width: 100%"
                  :disabled="readonly"
                />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="HTTPS 端口">
                <a-input-number
                  v-model:value="record.origin_https_port"
                  :min="1"
                  :max="65535"
                  style="width: 100%"
                  :disabled="readonly"
                />
              </a-form-item>
            </a-col>
          </a-row>

          <a-row :gutter="16">
            <a-col :span="12">
              <div class="fs-switch-row">
                <span>监听 HTTP</span>
                <a-switch v-model:checked="record.listen_http" :disabled="readonly" />
              </div>
            </a-col>
            <a-col :span="12">
              <div class="fs-switch-row">
                <span>监听 HTTPS</span>
                <a-switch v-model:checked="record.listen_https" :disabled="readonly" />
              </div>
            </a-col>
          </a-row>

          <template v-if="record.listen_https">
            <a-form-item label="SSL 证书" required>
              <template v-if="certOptions.length">
                <a-select
                  v-model:value="record.certificate_id"
                  placeholder="请选择证书"
                  style="width: 100%"
                  :options="certSelectOptions"
                  allow-clear
                  :disabled="readonly"
                />
              </template>
              <a-empty v-else-if="!readonly" description="暂无可用证书" :image-style="{ height: '48px' }">
                <a-button type="primary" size="small" @click="goCertificates">前往证书管理</a-button>
              </a-empty>
              <span v-else>{{ certName(record.certificate_id) }}</span>
            </a-form-item>
            <div class="fs-switch-row" style="margin-bottom: 16px">
              <span>强制 HTTPS</span>
              <a-switch v-model:checked="record.force_https" :disabled="readonly" />
            </div>
            <a-alert
              v-if="record.force_https"
              type="info"
              show-icon
              style="margin-bottom: 16px"
              message="已开启强制 HTTPS：HTTP 请求将自动 301 跳转到 HTTPS，不再经 WAF 代理处理。"
            />
          </template>
        </fs-form-section>

        <fs-form-section title="自定义防护页面" description="关闭时使用系统设置中的全局防护页面；优先级低于规则/黑名单/限速的专属配置">
          <div class="fs-switch-row">
            <span>启用站点专属防护页面</span>
            <a-switch v-model:checked="record.custom_block_page_enabled" :disabled="readonly" />
          </div>
          <template v-if="record.custom_block_page_enabled">
            <a-row :gutter="16">
              <a-col :span="8">
                <a-form-item label="响应状态码">
                  <a-select
                    v-model:value="record.block_page_status_code"
                    :disabled="readonly"
                    :options="blockStatusOptions"
                  />
                </a-form-item>
              </a-col>
            </a-row>
            <a-form-item label="HTML 内容">
              <a-textarea
                v-model:value="record.block_page_html"
                :rows="10"
                :disabled="readonly"
                class="fs-code-textarea"
              />
            </a-form-item>
          </template>
        </fs-form-section>

        <fs-form-section title="自定义人机验证页脚" description="关闭时使用系统设置中的全局页脚代码">
          <div class="fs-switch-row">
            <span>启用站点专属页脚</span>
            <a-switch v-model:checked="record.custom_captcha_footer_enabled" :disabled="readonly" />
          </div>
          <template v-if="record.custom_captcha_footer_enabled">
            <a-form-item label="页脚 HTML">
              <a-textarea
                v-model:value="record.captcha_footer_html"
                :rows="4"
                :disabled="readonly"
                class="fs-code-textarea"
              />
            </a-form-item>
          </template>
        </fs-form-section>
      </div>
    </template>
  </resource-crud>
  </page-shell>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import PageShell from "@/components/PageShell.vue";
import ResourceCrud from "@/components/ResourceCrud.vue";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import OriginHostInput from "@/components/OriginHostInput.vue";
import SiteCard, { type SiteCardMetrics } from "@/components/SiteCard.vue";
import { enabledFilterOptions } from "@/constants/resourceList";
import { commonBatchEditFields } from "@/constants/batch";
import { CLIENT_IP_SOURCE_OPTIONS } from "@/constants/clientIpSource";
import { useLogNavigation } from "@/composables/useLogNavigation";
import type { ResourceQuickAction } from "@/composables/useResourceQuickActions";
import { api } from "@/api";
import type { BatchConfig } from "@/types/batch";
import type { ResourceColumn, ResourceFilterField } from "@/types/resourceList";

interface CertOption {
  id: number;
  name: string;
  domains: string | null;
  not_after: string | null;
}

const router = useRouter();
const { goToLogs } = useLogNavigation();
const crudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);
const certOptions = ref<CertOption[]>([]);
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

function clientIpSourceExtra(source: string | null | undefined) {
  if (source && source !== "remote_addr") {
    return "使用了 CDN 或反代时，需选择与上游一致的 IP 来源头。仅可信上游可直连引擎。";
  }
  return "使用了 CDN 或反代时，需选择与上游一致的 IP 来源头";
}

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
  if (row.force_https && !row.listen_https) {
    throw new Error("开启强制 HTTPS 需要先开启 HTTPS 监听");
  }
  if (!row.listen_https) {
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

function goCertificates() {
  router.push("/certificates");
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

@media (max-width: 767px) {
  .site-card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
