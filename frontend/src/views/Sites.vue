<template>
  <page-shell title="站点管理" description="配置防护域名、回源地址、HTTPS 证书与自定义拦截页">
    <template #actions>
      <a-button type="primary" @click="crudRef?.openCreate()">新增站点</a-button>
    </template>
    <resource-crud ref="crudRef" embedded title="站点管理" api-base="/api/v1/sites" :columns="columns" :filters="filters"
      :default-record="defaultRecord" :prepare-payload="preparePayload" :batch="batchConfig" name-field="name"
      detail-actions duplicatable :extra-create-tabs="panelImportTabs" :extra-create-footer="panelImportFooter"
      :hide-list-pagination="listStyle === 'table'"
      @mutated="invalidateSiteOptions" @extra-create-ok="onPanelImportOk">
      <template #filter-extra>
        <a-tooltip :title="listStyle === 'card' ? '切换为表格' : '切换为卡片'">
          <a-button :aria-label="listStyle === 'card' ? '切换为表格' : '切换为卡片'" @click="toggleListStyle">
            <template #icon>
              <unordered-list-outlined v-if="listStyle === 'card'" />
              <appstore-outlined v-else />
            </template>
          </a-button>
        </a-tooltip>
      </template>
      <template
        #list="{ rows, loading, openView, openEdit, openDuplicate, remove, toggleEnabled, togglingId, allowDelete, nameActions, duplicatable: canDuplicate, pagination, onTableChange, sortField, sortOrder, onRefresh }">
        <fs-data-table
          v-if="listStyle === 'table'"
          :columns="siteTableColumns(sortField, sortOrder)"
          :data-source="rows"
          :loading="loading || (metricsLoading && !Object.keys(metricsMap).length)"
          :pagination="pagination"
          api-base="/api/v1/sites"
          :batch="batchConfig"
          has-enabled-column
          mobile-title-key="name"
          :mobile-exclude-keys="siteTableMobileExcludeKeys"
          :scroll="{ x: 1280 }"
          @change="onTableChange"
          @refresh="onRefresh"
        >
          <template #head="{ record }">
            <a class="site-mobile-title" @click="openView(record)">
              {{ record.name }}
              <a-tag v-if="metricsMap[String(record.id)]?.anomaly" color="error">异常流量</a-tag>
            </a>
          </template>
          <template #bodyCell="{ column, record, text }">
            <template v-if="column.dataIndex === 'name'">
              <div class="site-table-name">
                <resource-name-cell
                  :text="String(text ?? '')"
                  :actions="nameActions(record)"
                  @view="openView(record)"
                />
                <a-tag v-if="metricsMap[String(record.id)]?.anomaly" color="error">异常流量</a-tag>
              </div>
            </template>
            <template v-else-if="column.key === 'domains'">
              {{ record.domains_display || (record.domains || []).join("、") || "—" }}
            </template>
            <template v-else-if="column.key === 'listen'">
              <template v-if="listenTags(record).length">
                <a-tag v-for="tag in listenTags(record)" :key="tag.text" :color="tag.color">{{ tag.text }}</a-tag>
              </template>
              <template v-else>—</template>
            </template>
            <template v-else-if="column.key === 'certificate'">
              {{ record.certificate_name || "未绑定" }}
            </template>
            <template v-else-if="column.key === 'client_ip'">
              {{ clientIpSourceLabel(record.client_ip_source) }}
            </template>
            <template v-else-if="column.key === 'requests_24h'">
              {{ formatMetricCount(metricsMap[String(record.id)]?.requests_24h) }}
            </template>
            <template v-else-if="column.key === 'blocked_24h'">
              {{ formatMetricCount(metricsMap[String(record.id)]?.blocked_24h) }}
            </template>
            <template v-else-if="column.key === 'enabled'">
              <a-switch
                :checked="record.enabled"
                :loading="togglingId === record.id"
                @change="(checked: boolean) => onTableEnabledChange(record, checked, toggleEnabled)"
              />
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-button size="small" type="primary" ghost @click="openEdit(record)">编辑</a-button>
              <a-button v-if="canDuplicate" size="small" @click="openDuplicate(record)">复制</a-button>
              <span v-if="tableMobileMoreActions(record, nameActions).length" class="mobile-card-more">
                <a-dropdown :arrow="true">
                  <a-button size="small">更多</a-button>
                  <template #overlay>
                    <a-menu :selectable="false">
                      <template v-for="(action, index) in tableMobileMoreActions(record, nameActions)" :key="action.key">
                        <a-menu-divider v-if="action.divided && index > 0" />
                        <a-menu-item :danger="action.danger" @click="() => runAction(action)">
                          {{ action.label }}
                        </a-menu-item>
                      </template>
                    </a-menu>
                  </template>
                </a-dropdown>
              </span>
            </template>
            <template v-else>
              {{ text ?? "—" }}
            </template>
          </template>
        </fs-data-table>
        <a-spin v-else :spinning="loading || (metricsLoading && !Object.keys(metricsMap).length)">
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
                    placeholder="输入域名后回车，支持多个，支持泛解析" style="width: 100%" :disabled="readonly" />
                </a-form-item>
              </a-col>
            </a-row>
          </fs-form-section>
          <fs-form-section title="回源配置">
            <a-row :gutter="16">
              <a-col :md="12" :lg="12" :xs="16">
                <a-form-item label="源站地址" required>
                  <origin-host-input v-model:value="record.origin_host" :disabled="readonly" />
                </a-form-item>
              </a-col>
              <a-col :md="4" :lg="4" :xs="8">
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
              <div class="fs-switch-row-header">
                <div>
                  <div><b>修改访问监控端口</b></div>
                  <div class="fs-muted">系统默认监控 80 和 443 端口，如您的访问端口不同，可以在此修改</div>
                </div>
                <a-switch v-model:checked="record.custom_listen_ports" :disabled="readonly"
                  @change="(checked) => onCustomListenPortsChange(record, checked)" />
              </div>
              <div class="fs-switch-row-body" v-if="record.custom_listen_ports">
                <a-row :gutter="16">
                  <a-col :md="12" :lg="12" :xs="24">
                    <a-form-item label="HTTP 访问端口">
                      <a-select v-model:value="record.listen_http_ports" mode="tags" :open="false"
                        :token-separators="[]" placeholder="输入端口后回车，可添加多个" style="width: 100%"
                        :disabled="readonly || !record.listen_http" @inputKeyDown="onListenPortKeyDown"
                        @change="(v) => { record.listen_http_ports = sanitizeListenPorts(v) }" />
                    </a-form-item>
                  </a-col>
                  <a-col :md="12" :lg="12" :xs="24">
                    <a-form-item label="HTTPS 访问端口">
                      <a-select v-model:value="record.listen_https_ports" mode="tags" :open="false"
                        :token-separators="[]" placeholder="输入端口后回车，可添加多个" style="width: 100%"
                        :disabled="readonly || !record.listen_https" @inputKeyDown="onListenPortKeyDown"
                        @change="(v) => { record.listen_https_ports = sanitizeListenPorts(v) }" />
                    </a-form-item>
                  </a-col>
                </a-row>
                <a-alert type="warning" show-icon style="margin-bottom: 0px"
                  message="修改的端口请确保已在docker中映射，且已在防火墙和安全组放行" />
              </div>
            </div>
            <div class="fs-switch-row">
              <div class="fs-switch-row-header">
                <div>
                  <div><b>关闭内容缓冲</b></div>
                  <div class="fs-muted">如果源站在本机，启用后可降低内存占用</div>
                </div>
                <a-switch v-model:checked="record.disable_content_buffering" :disabled="readonly" />
              </div>
            </div>
            <div class="fs-switch-row">
              <div class="fs-switch-row-header">
                <div>
                  <div><b>自定义拦截页面</b></div>
                  <div class="fs-muted">为此站点自定义拦截页面内容，优先级低于规则/黑名单/限速的专属配置</div>
                </div>
                <a-switch v-model:checked="record.custom_block_page_enabled" :disabled="readonly" />
              </div>
              <div class="fs-switch-row-body" v-if="record.custom_block_page_enabled">
                <a-form-item label="响应状态码">
                  <a-select v-model:value="record.block_page_status_code" :disabled="readonly"
                    :options="blockStatusOptions" />
                </a-form-item>
                <a-form-item label="HTML 内容">
                  <a-textarea v-model:value="record.block_page_html" :rows="10" :disabled="readonly"
                    class="fs-code-textarea" />
                </a-form-item>
              </div>
            </div>
            <div class="fs-switch-row">
              <div class="fs-switch-row-header">
                <div>
                  <div><b>自定义人机验证页脚</b></div>
                  <div class="fs-muted">为此站点自定义人机验证页面的底部页脚显示内容，优先级低于规则/黑名单/限速的专属配置</div>
                </div>
                <a-switch v-model:checked="record.custom_captcha_footer_enabled" :disabled="readonly" />
              </div>
              <div class="fs-switch-row-body" v-if="record.custom_captcha_footer_enabled">
                <a-form-item label="页脚 HTML">
                  <a-textarea v-model:value="record.captcha_footer_html" :rows="4" :disabled="readonly"
                    class="fs-code-textarea" />
                </a-form-item>
              </div>
            </div>
          </fs-form-section>
        </div>
      </template>
      <template #create-tab-extra="{ tabKey }">
        <panel-import-form ref="panelImportRef" kind="sites" :provider="tabKey === 'onepanel' ? 'onepanel' : 'baota'"
          @status="onPanelStatus" @imported="onPanelImported" @close="crudRef?.closeDrawer()" />
      </template>
    </resource-crud>

    <certificate-form-drawer v-model:open="certDrawerOpen" :z-index="1100"
      :preselect-site-id="certPreselectSiteId" :opened-from-site="Boolean(certSelectRecord)"
      @saved="onCertImported" @imported="onCertPanelImported" />
  </page-shell>
</template>

<script setup lang="ts">
import { computed, defineComponent, onMounted, onUnmounted, reactive, ref } from "vue";
import { Modal } from "ant-design-vue";
import { AppstoreOutlined, PlusOutlined, UnorderedListOutlined } from "@ant-design/icons-vue";
import PageShell from "@/components/PageShell.vue";
import ResourceCrud from "@/components/ResourceCrud.vue";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsDataTable from "@/components/FsDataTable.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import OriginHostInput from "@/components/OriginHostInput.vue";
import CertificateFormDrawer, { type CertificateSaved } from "@/components/CertificateFormDrawer.vue";
import PanelImportForm, { type PanelImportStatus } from "@/components/PanelImportForm.vue";
import ResourceNameCell from "@/components/ResourceNameCell.vue";
import SiteCard, { type SiteCardMetrics } from "@/components/SiteCard.vue";
import { enabledFilterOptions } from "@/constants/resourceList";
import { commonBatchEditFields } from "@/constants/batch";
import { CLIENT_IP_SOURCE_OPTIONS, clientIpSourceLabel } from "@/constants/clientIpSource";
import { useLogNavigation } from "@/composables/useLogNavigation";
import { useResponsivePagination } from "@/composables/useResponsivePagination";
import { invalidateSiteOptions } from "@/composables/useSiteOptions";
import { useResourceQuickActions, type ResourceQuickAction } from "@/composables/useResourceQuickActions";
import { api } from "@/api";
import { useAppSettingsStore } from "@/stores/appSettings";
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
const { runAction } = useResourceQuickActions();
const { isMobile } = useResponsivePagination();
const appSettings = useAppSettingsStore();
const crudRef = ref<InstanceType<typeof ResourceCrud> | null>(null);
const certOptions = ref<CertOption[]>([]);
const certDrawerOpen = ref(false);
const certSelectRecord = ref<Record<string, any> | null>(null);
const certPreselectSiteId = computed(() => {
  const id = Number(certSelectRecord.value?.id);
  return Number.isFinite(id) && id > 0 ? id : null;
});
const panelImportRef = ref<{ submit: () => Promise<void> } | null>(null);
const panelImportTabs = [
  { key: "baota", tab: "从宝塔导入" },
  { key: "onepanel", tab: "从 1Panel 导入" },
];
const panelStatus = reactive<PanelImportStatus>({
  canImport: false,
  okText: "导入",
  importing: false,
  loading: false,
});
const panelImportFooter = computed(() => ({
  okText: panelStatus.okText,
  hideOk: !panelStatus.canImport,
  confirmLoading: panelStatus.importing,
  loading: panelStatus.loading,
}));
const metricsLoading = ref(false);
const metricsMap = reactive<Record<string, SiteCardMetrics>>({});
let metricsTimer: ReturnType<typeof setInterval> | null = null;
const LIST_STYLE_KEY = "fs-sites-list-style";

/**
 * 读取上次保存的站点列表样式；无效或读失败时用卡片。
 *
 * @return card 或 table
 */
function readListStyle(): "card" | "table" {
  try {
    return localStorage.getItem(LIST_STYLE_KEY) === "table" ? "table" : "card";
  } catch {
    return "card";
  }
}

const listStyle = ref<"card" | "table">(readListStyle());

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

/**
 * 把当前排序状态映射成 Ant Design 列的 sortOrder。
 *
 * @param sortField 当前排序字段
 * @param sortOrder 当前排序方向
 * @param key 列字段
 * @return ascend / descend / undefined
 */
function sortOrderOf(sortField: unknown, sortOrder: unknown, key: string) {
  if (sortField !== key || !sortOrder) return undefined;
  return sortOrder === "asc" ? "ascend" : "descend";
}

/**
 * 表格模式列：对齐站点卡片上的常用信息。
 *
 * @param sortField 当前排序字段
 * @param sortOrder 当前排序方向
 * @return 表格列
 */
function siteTableColumns(sortField: unknown, sortOrder: unknown) {
  const cols: any[] = [
    {
      title: "名称",
      dataIndex: "name",
      sorter: true,
      sortOrder: sortOrderOf(sortField, sortOrder, "name"),
      width: 180,
    },
    { title: "域名", key: "domains", dataIndex: "domains_display", ellipsis: true, sorter: true, sortOrder: sortOrderOf(sortField, sortOrder, "domains_display") },
    { title: "源站", dataIndex: "origin_display", ellipsis: true },
    { title: "监听", key: "listen", width: 180 },
    { title: "证书", key: "certificate", ellipsis: true, width: 140 },
    { title: "客户端 IP", key: "client_ip", width: 160, ellipsis: true },
    { title: "24H请求量", key: "requests_24h", width: 110 },
    { title: "24H拦截量", key: "blocked_24h", width: 110 },
    { title: "状态", key: "enabled", dataIndex: "enabled", width: 90, sorter: true, sortOrder: sortOrderOf(sortField, sortOrder, "enabled") },
  ];
  if (isMobile.value) {
    cols.push({ title: "操作", key: "actions" });
  }
  return cols;
}

const siteTableMobileExcludeKeys = ["actions", "enabled"];

/**
 * 移动端表格卡片底部「更多」：去掉已单独展示的编辑、复制。
 *
 * @param site 站点行
 * @param nameActions ResourceCrud 名称菜单生成函数
 * @return 更多菜单项
 */
function tableMobileMoreActions(
  site: Record<string, any>,
  nameActions: (row: Record<string, any>) => ResourceQuickAction[],
) {
  return nameActions(site).filter((action) => action.key !== "edit" && action.key !== "duplicate");
}

// 在卡片 / 表格两种列表样式之间切换，并写入浏览器本地
function toggleListStyle() {
  listStyle.value = listStyle.value === "card" ? "table" : "card";
  try {
    localStorage.setItem(LIST_STYLE_KEY, listStyle.value);
  } catch {
    /* ignore */
  }
}

/**
 * 站点监听方式标签，与卡片一致。
 *
 * @param site 站点行
 * @return 监听标签
 */
function listenTags(site: Record<string, any>) {
  const tags: { text: string; color?: string }[] = [];
  if (site.listen_http) tags.push({ text: "HTTP" });
  if (site.listen_https && !site.force_https) tags.push({ text: "HTTPS", color: "blue" });
  if (site.force_https) tags.push({ text: "强制HTTPS", color: "purple" });
  return tags;
}

/**
 * 压缩展示 24 小时指标。
 *
 * @param value 计数
 * @return 展示文本
 */
function formatMetricCount(value: number | null | undefined) {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 10_000) return `${(value / 1000).toFixed(1)}k`;
  if (value >= 1000) return `${(value / 1000).toFixed(2)}k`;
  return String(value);
}

const certSelectOptions = computed(() =>
  certOptions.value.map((c) => ({
    value: c.id,
    label: c.domains ? `${c.name}（${c.domains}）` : c.name,
  })),
);

function currentBrowserPort(): number | null {
  const raw = window.location.port;
  if (raw && /^\d+$/.test(raw)) return Number(raw);
  return null;
}

function reservedListenPortMessages(): Record<number, string> {
  const reserved: Record<number, string> = {};
  const apiPort = Number(appSettings.backendPort) || 0;
  const panelPort = currentBrowserPort() || Number(appSettings.panelPort) || 0;
  if (apiPort) {
    reserved[apiPort] = `端口 ${apiPort} 为系统内部接口，请换一个`;
  }
  if (panelPort && !reserved[panelPort]) {
    reserved[panelPort] = `端口 ${panelPort} 为管理面板占用，请换一个`;
  }
  return reserved;
}

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
  custom_listen_ports: false,
  listen_http_ports: [80] as number[],
  listen_https_ports: [443] as number[],
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
  row.listen_http_ports = sanitizeListenPorts(row.listen_http_ports);
  row.listen_https_ports = sanitizeListenPorts(row.listen_https_ports);
  if (row.custom_listen_ports) {
    if (row.listen_http && !row.listen_http_ports.length) {
      throw new Error("开启自定义访问端口后，HTTP 监听至少需要一个端口");
    }
    if (row.listen_https && !row.listen_https_ports.length) {
      throw new Error("开启自定义访问端口后，HTTPS 监听至少需要一个端口");
    }
    if (row.listen_http && row.listen_https) {
      const overlap = row.listen_http_ports.filter((port: number) =>
        row.listen_https_ports.includes(port)
      );
      if (overlap.length) {
        throw new Error(`HTTP 与 HTTPS 不能使用相同端口：${overlap.join("、")}`);
      }
    }
    const reserved = reservedListenPortMessages();
    const used = [
      ...(row.listen_http ? row.listen_http_ports : []),
      ...(row.listen_https ? row.listen_https_ports : []),
    ];
    for (const port of used) {
      if (reserved[port]) throw new Error(reserved[port]);
    }
  }
  if (!row.listen_http_ports.length) row.listen_http_ports = [80];
  if (!row.listen_https_ports.length) row.listen_https_ports = [443];
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

function sanitizeListenPorts(values: unknown): number[] {
  const list = Array.isArray(values) ? values : [];
  const seen = new Set<number>();
  const ports: number[] = [];
  for (const item of list) {
    const text = String(item ?? "").trim();
    if (!/^\d+$/.test(text)) continue;
    const port = Number(text);
    if (port < 1 || port > 65535 || seen.has(port)) continue;
    seen.add(port);
    ports.push(port);
  }
  return ports;
}

function onListenPortKeyDown(e: KeyboardEvent) {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (
    e.key === "Backspace" ||
    e.key === "Delete" ||
    e.key === "Tab" ||
    e.key === "Enter" ||
    e.key === "Escape" ||
    e.key === "ArrowLeft" ||
    e.key === "ArrowRight" ||
    e.key === "Home" ||
    e.key === "End"
  ) {
    return;
  }
  if (e.key.length === 1 && /^\d$/.test(e.key)) return;
  e.preventDefault();
}

function onCustomListenPortsChange(record: Record<string, any>, checked: boolean) {
  if (!checked) return;
  if (!sanitizeListenPorts(record.listen_http_ports).length) {
    record.listen_http_ports = [80];
  } else {
    record.listen_http_ports = sanitizeListenPorts(record.listen_http_ports);
  }
  if (!sanitizeListenPorts(record.listen_https_ports).length) {
    record.listen_https_ports = [443];
  } else {
    record.listen_https_ports = sanitizeListenPorts(record.listen_https_ports);
  }
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

function onPanelStatus(status: PanelImportStatus) {
  Object.assign(panelStatus, status);
}

function onPanelImportOk() {
  void panelImportRef.value?.submit();
}

function onPanelImported() {
  invalidateSiteOptions();
  crudRef.value?.closeDrawer();
  crudRef.value?.fetchList();
  void loadCertOptions();
}

async function onCertPanelImported() {
  await loadCertOptions();
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

/**
 * 表格中切换启用状态；停用前确认，避免只当关闭检测。
 *
 * @param site 站点行
 * @param enabled 目标状态
 * @param toggleEnabled ResourceCrud 提供的持久化函数
 */
function onTableEnabledChange(
  site: Record<string, any>,
  enabled: boolean,
  toggleEnabled: (row: Record<string, any>, enabled: boolean) => void,
) {
  if (enabled) {
    toggleEnabled(site, true);
    return;
  }
  Modal.confirm({
    title: "确认停用站点？",
    content: "停用后将从引擎移除 Nginx 配置，该域名将无法访问（并非仅关闭 WAF 检测）。",
    okText: "确认停用",
    okType: "danger",
    cancelText: "取消",
    onOk: () => toggleEnabled(site, false),
  });
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

.site-table-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.site-mobile-title {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  line-height: 1.4;
  color: var(--fs-color-primary);
  word-break: break-word;
}

.mobile-card-more {
  margin-left: auto;
}

.site-listen-addon {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.site-listen-port :deep(.ant-input-number-group-addon):first-child {
  width: 98px;
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

  .site-listen-port {
    margin-bottom: 6px;
  }
}
</style>
