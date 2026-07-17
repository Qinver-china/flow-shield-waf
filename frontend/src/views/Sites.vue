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
            <a-col :span="12">
              <a-form-item label="域名" required>
                <a-input v-model:value="record.domain" placeholder="example.com" :disabled="readonly" />
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
          </template>
        </fs-form-section>

        <fs-form-section title="自定义防护页面" description="关闭时使用系统设置中的全局防护页面">
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
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import PageShell from "@/components/PageShell.vue";
import ResourceCrud from "@/components/ResourceCrud.vue";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import OriginHostInput from "@/components/OriginHostInput.vue";
import { enabledFilterOptions } from "@/constants/resourceList";
import { commonBatchEditFields } from "@/constants/batch";
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
const crudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);
const certOptions = ref<CertOption[]>([]);

const protocolOptions = [
  { value: "follow", label: "跟随协议" },
  { value: "http", label: "HTTP" },
  { value: "https", label: "HTTPS" },
];

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
  { title: "域名", dataIndex: "domain", sorter: true },
  { title: "源站", dataIndex: "origin_display" },
  { title: "证书", dataIndex: "certificate_name", width: 140 },
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
  domain: "",
  origin_host: "",
  origin_protocol: "follow",
  origin_http_port: 80,
  origin_https_port: 443,
  listen_http: true,
  listen_https: false,
  certificate_id: null as number | null,
  enabled: true,
  custom_block_page_enabled: false,
  block_page_status_code: 403,
  block_page_html: "",
  custom_captcha_footer_enabled: false,
  captcha_footer_html: "",
});

function preparePayload(row: Record<string, any>) {
  if (!row.listen_http && !row.listen_https) {
    throw new Error("至少需要开启 HTTP 或 HTTPS 监听");
  }
  if (row.listen_https && !row.certificate_id) {
    throw new Error("开启 HTTPS 时必须选择 SSL 证书");
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

function goCertificates() {
  router.push("/certificates");
}

function certName(id: number | null) {
  if (!id) return "-";
  const cert = certOptions.value.find((c) => c.id === id);
  return cert ? (cert.domains ? `${cert.name}（${cert.domains}）` : cert.name) : `#${id}`;
}

onMounted(loadCertOptions);
</script>

<style scoped>
/* layout handled by form-surfaces.css */
</style>
