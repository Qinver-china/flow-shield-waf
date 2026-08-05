<template>
  <article
    class="site-card"
    :class="{ 'site-card--disabled': !site.enabled, 'site-card--anomaly': metrics?.anomaly }"
  >
    <header class="site-card__head">
      <div
        class="site-card__title-wrap"
      >
        <button type="button" class="site-card__title" @click="emit('view')">
          {{ site.name }}
        </button>
        <a-tag :color="site.enabled ? 'success' : 'error'" class="site-card__status">
          {{ site.enabled ? "已启用" : "已停用" }}
        </a-tag>
        <a-tag v-if="metrics?.anomaly" color="error" class="site-card__status">异常流量</a-tag>
      </div>
      <a-switch
        :checked="site.enabled"
        :loading="toggling"
        @change="onToggleChange"
      />
    </header>

    <div
      class="site-card__domains"
    >
      <template v-if="domainList.length">
        <template v-for="(domain, index) in domainList" :key="domain">
          <a
            class="site-card__domain-link"
            :href="domainHref(domain)"
            target="_blank"
            rel="noopener noreferrer"
            :title="`打开 ${domainHref(domain)}`"
          >{{ domain }}</a>
          <span v-if="index < domainList.length - 1" class="site-card__domain-sep"> · </span>
        </template>
      </template>
      <span v-else>未配置域名</span>
    </div>

    <div class="site-card__meta">
      <div
        v-for="item in metaItems"
        :key="item.label"
        class="meta-item"
      >
        <span class="meta-label">{{ item.label }}</span>
        <span class="meta-value" :title="item.tags?.length ? undefined : String(item.value || '')">
          <template v-if="item.tags?.length">
            <a-tag v-for="tag in item.tags" :key="tag.text" :color="tag.color" class="proto-tag">
              {{ tag.text }}
            </a-tag>
          </template>
          <template v-else>{{ item.value }}</template>
        </span>
      </div>
    </div>

    <div class="site-card__metrics">
      <button
        type="button"
        class="metric metric--clickable"
        title="查看近 24 小时统计"
        @click="goStats({})"
      >
        <div
          class="metric__value"
        >
          {{ formatCount(metrics?.requests_24h) }}
        </div>
        <div class="metric__label">24 小时命中量</div>
        <div
          class="metric__delta"
          :class="deltaClass(metrics?.requests_24h_delta_pct)"
        >
          {{ formatDelta(metrics?.requests_24h_delta_pct) }}
        </div>
      </button>
      <button
        type="button"
        class="metric metric--danger metric--clickable"
        title="查看近 24 小时拦截统计"
        @click="goStats({ blocked: true })"
      >
        <div
          class="metric__value"
        >
          {{ formatCount(metrics?.blocked_24h) }}
        </div>
        <div class="metric__label">24 小时拦截数量</div>
        <div
          class="metric__delta"
          :class="deltaClass(metrics?.blocked_24h_delta_pct)"
        >
          {{ formatDelta(metrics?.blocked_24h_delta_pct) }}
        </div>
      </button>
      <button
        type="button"
        class="metric metric--clickable"
        title="按客户端 IP 聚合统计"
        @click="goStats({ dimension: 'client_ip' })"
      >
        <div
          class="metric__value"
        >
          {{ formatCount(metrics?.unique_ips_24h) }}
        </div>
        <div class="metric__label">24 小时 IP 数量</div>
        <div
          class="metric__delta"
          :class="deltaClass(metrics?.unique_ips_24h_delta_pct)"
        >
          {{ formatDelta(metrics?.unique_ips_24h_delta_pct) }}
        </div>
      </button>
    </div>

    <div v-if="trafficWindows.length" class="site-card__traffic">
      <div class="site-card__traffic-title">实时流量</div>
      <div class="site-card__traffic-grid">
        <div
          v-for="w in trafficWindows"
          :key="w.window_sec"
          class="traffic-card"
          :class="trafficBaselineClass(w)"
        >
          <div class="traffic-card__label">{{ w.label }}</div>
          <div
            class="traffic-card__value"
          >
            {{ formatCount(w.requests) }}
            <span class="traffic-card__qps">{{ formatQps(w.qps) }}</span>
          </div>
          <a-tooltip
            :title="trafficBaselineTip(w)"
            overlay-class-name="baseline-status-tooltip"
            :mouse-enter-delay="0.25"
          >
            <div class="traffic-card__baseline">
              <template v-if="w.baseline_avg != null">
                <div class="traffic-card__baseline-line">
                  基线 {{ formatBaseline(w.baseline_avg) }}
                </div>
                <div
                  v-if="w.deviation_ratio != null"
                  class="traffic-card__deviation"
                >
                  <ArrowUpOutlined
                    v-if="deviationDelta(w.deviation_ratio) > 0"
                    class="traffic-card__deviation-icon"
                  />
                  <ArrowDownOutlined
                    v-else-if="deviationDelta(w.deviation_ratio) < 0"
                    class="traffic-card__deviation-icon"
                  />
                  <span>{{ formatDeviation(w.deviation_ratio) }}</span>
                </div>
              </template>
              <template v-else>暂无基线</template>
            </div>
          </a-tooltip>
        </div>
      </div>
    </div>

    <footer class="site-card__actions">
      <a-button type="link" size="small" @click="emit('view')">查看</a-button>
      <a-button type="link" size="small" @click="emit('edit')">编辑</a-button>
      <a-button type="link" size="small" @click="emit('logs')">日志</a-button>
      <a-button type="link" size="small" @click="goStats({})">统计</a-button>
      <span class="site-card__more">
        <a-dropdown>
          <a-button type="link" size="small">更多</a-button>
          <template #overlay>
            <a-menu :selectable="false">
              <a-menu-item v-for="action in menuActions" :key="action.key" @click="() => runAction(action)">
                <span :class="{ danger: action.danger }">{{ action.label }}</span>
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </span>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Modal } from "ant-design-vue";
import { ArrowDownOutlined, ArrowUpOutlined } from "@ant-design/icons-vue";
import { clientIpSourceLabel } from "@/constants/clientIpSource";
import { useLogNavigation } from "@/composables/useLogNavigation";
import type { ResourceQuickAction } from "@/composables/useResourceQuickActions";
import { useResourceQuickActions } from "@/composables/useResourceQuickActions";
import { baselineTone } from "@/utils/baselineTone";

export type SiteTrafficWindow = {
  window_sec: number;
  label: string;
  requests: number;
  qps: number;
  threshold?: number | null;
  baseline_avg?: number | null;
  baseline_warmup?: boolean;
  deviation_ratio?: number | null;
  is_anomaly?: boolean;
};

export type SiteCardMetrics = {
  requests_24h: number;
  requests_24h_delta_pct?: number | null;
  blocked_24h: number;
  blocked_24h_delta_pct?: number | null;
  unique_ips_24h: number;
  unique_ips_24h_delta_pct?: number | null;
  block_rate?: number;
  traffic_windows?: SiteTrafficWindow[];
  anomaly?: boolean;
};

const props = withDefaults(
  defineProps<{
    site: Record<string, any>;
    metrics?: SiteCardMetrics | null;
    toggling?: boolean;
    moreActions?: ResourceQuickAction[];
  }>(),
  {
    moreActions: () => [],
  },
);

const emit = defineEmits<{
  view: [];
  edit: [];
  logs: [];
  "toggle-enabled": [enabled: boolean];
}>();

const { runAction } = useResourceQuickActions();
const { goToLogs } = useLogNavigation("24h");

const domainList = computed(() => {
  if (Array.isArray(props.site.domains) && props.site.domains.length) {
    return props.site.domains.map((d: string) => String(d).trim()).filter(Boolean);
  }
  const raw = String(props.site.domains_display || props.site.domain || "").trim();
  if (!raw) return [] as string[];
  return raw.split(/[,\s·]+/).map((d) => d.trim()).filter(Boolean);
});

const siteScheme = computed(() => (props.site.listen_https ? "https" : "http"));

function domainHref(domain: string) {
  const host = domain.replace(/^https?:\/\//i, "").replace(/\/$/, "");
  return `${siteScheme.value}://${host}`;
}

const metaItems = computed(() => {
  const listenTags: { text: string; color?: string }[] = [];
  if (props.site.listen_http) listenTags.push({ text: "HTTP" });
  if (props.site.listen_https && !props.site.force_https) listenTags.push({ text: "HTTPS", color: "blue" });
  if (props.site.force_https) listenTags.push({ text: "强制HTTPS", color: "purple" });

  return [
    { label: "源站", value: props.site.origin_display || "—" },
    {
      label: "监听",
      value: listenTags.length ? "" : "—",
      tags: listenTags.length ? listenTags : undefined,
    },
    { label: "证书", value: props.site.certificate_name || "未绑定" },
    { label: "客户端 IP", value: clientIpSourceLabel(props.site.client_ip_source) },
  ];
});

const trafficWindows = computed(() => props.metrics?.traffic_windows || []);

const menuActions = computed(() => props.moreActions || []);

function onToggleChange(checked: boolean) {
  if (checked) {
    emit("toggle-enabled", true);
    return;
  }
  Modal.confirm({
    title: "确认停用站点？",
    content: "停用后将从引擎移除 Nginx 配置，该域名将无法访问（并非仅关闭 WAF 检测）。",
    okText: "确认停用",
    okType: "danger",
    cancelText: "取消",
    onOk: () => emit("toggle-enabled", false),
  });
}

function goStats(filters: { blocked?: boolean; dimension?: string }) {
  const siteId = Number(props.site.id);
  if (!Number.isFinite(siteId)) return;
  goToLogs({
    tab: "stats",
    preset: "24h",
    site_id: siteId,
    ...filters,
  });
}

function formatCount(value: number | null | undefined) {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 10_000) return `${(value / 1000).toFixed(1)}k`;
  if (value >= 1000) return `${(value / 1000).toFixed(2)}k`;
  return String(value);
}

function formatDelta(value: number | null | undefined) {
  if (value == null) return "较昨日 —";
  const sign = value > 0 ? "+" : "";
  return `较昨日 ${sign}${value}%`;
}

function deltaClass(value: number | null | undefined) {
  if (value == null || value === 0) return "metric__delta--flat";
  return value > 0 ? "metric__delta--up" : "metric__delta--down";
}

function formatQps(qps: number) {
  return `${qps.toFixed(1)} QPS`;
}

function formatBaseline(value: number) {
  return String(Math.round(value));
}

function deviationDelta(ratio: number) {
  return ratio * 100 - 100;
}

function formatDeviation(ratio: number) {
  const delta = deviationDelta(ratio);
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(0)}%`;
}

function trafficBaselineTip(w: SiteTrafficWindow) {
  if (w.baseline_avg == null) return "暂无可用基线";
  const parts = [`基线 ${formatBaseline(w.baseline_avg)}`];
  if (w.deviation_ratio != null) {
    parts.push(`相对 ${formatDeviation(w.deviation_ratio)}`);
  }
  parts.push(w.baseline_warmup ? "学习中" : "已稳定");
  return parts.join(" · ");
}

function trafficBaselineClass(w: SiteTrafficWindow) {
  const tone = baselineTone(w.deviation_ratio, w.baseline_warmup);
  if (tone === "warn") return "traffic-card--warn";
  if (tone === "danger") return "traffic-card--danger";
  return "";
}
</script>

<style scoped>
.site-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 18px 14px;
  border-radius: var(--fs-radius-md);
  background: var(--fs-bg-surface);
  border: 1px solid var(--fs-border);
  transition:
    box-shadow var(--fs-transition),
    transform var(--fs-transition),
    border-color var(--fs-transition);
}

.site-card--disabled {
  opacity: 0.6;
}

.site-card--anomaly {
  border-color: color-mix(in srgb, var(--fs-color-danger) 35%, var(--fs-border));
}

.site-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.site-card__title-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.site-card__title {
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--fs-text-primary);
  font-size: 17px;
  font-weight: 700;
  line-height: 1.3;
  cursor: pointer;
  text-align: left;
}

.site-card__title:hover {
  color: var(--fs-color-primary);
}

.site-card__status {
  margin: 0;
}

.site-card__domains {
  margin-top: -4px;
  color: var(--fs-color-primary);
  font-size: 13px;
  font-family: var(--fs-font-mono);
  line-height: 1.45;
  word-break: break-all;
}

.site-card__domain-link {
  color: var(--fs-color-primary);
  text-decoration: none;
  cursor: pointer;
}

.site-card__domain-link:hover {
  text-decoration: underline;
  color: var(--fs-color-primary-hover);
}

.site-card__domain-sep {
  color: var(--fs-text-muted);
}

.site-card__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 14px;
  padding: 12px;
  border-radius: var(--fs-radius-sm);
  background: var(--fs-bg-muted);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.meta-label {
  font-size: 11px;
  letter-spacing: 0.02em;
  color: var(--fs-text-muted);
  text-transform: uppercase;
}

.meta-value {
  font-size: 13px;
  color: var(--fs-text-secondary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.proto-tag {
  margin-inline-end: 4px;
}

.site-card__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.metric {
  padding: 10px 8px;
  border-radius: var(--fs-radius-sm);
  background: color-mix(in srgb, var(--fs-color-primary) 5%, var(--fs-bg-surface));
  border: 1px solid color-mix(in srgb, var(--fs-color-primary) 10%, var(--fs-border));
  text-align: center;
}

.metric--clickable {
  display: block;
  width: 100%;
  margin: 0;
  cursor: pointer;
  font: inherit;
  color: inherit;
  appearance: none;
  transition:
    transform var(--fs-transition),
    box-shadow var(--fs-transition),
    border-color var(--fs-transition),
    background var(--fs-transition);
}

.metric--clickable:hover {
  transform: translateY(-1px);
  box-shadow: var(--fs-shadow-sm);
  border-color: color-mix(in srgb, var(--fs-color-primary) 35%, var(--fs-border));
  background: color-mix(in srgb, var(--fs-color-primary) 10%, var(--fs-bg-surface));
}

.metric--clickable:focus-visible {
  outline: 2px solid var(--fs-color-primary);
  outline-offset: 2px;
}

.metric--danger.metric--clickable:hover {
  border-color: color-mix(in srgb, var(--fs-color-danger) 40%, var(--fs-border));
  background: color-mix(in srgb, var(--fs-color-danger) 12%, var(--fs-bg-surface));
}

.metric--danger {
  background: color-mix(in srgb, var(--fs-color-danger) 6%, var(--fs-bg-surface));
  border-color: color-mix(in srgb, var(--fs-color-danger) 16%, var(--fs-border));
}

.metric--danger .metric__value {
  color: var(--fs-color-danger);
}

.metric__value {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--fs-text-primary);
  font-variant-numeric: tabular-nums;
}

.metric__label {
  margin-top: 4px;
  font-size: 11px;
  color: var(--fs-text-muted);
}

.metric__delta {
  margin-top: 4px;
  font-size: 10px;
  line-height: 1.3;
  color: var(--fs-text-secondary);
}

.metric__delta--up {
  color: var(--fs-color-danger);
}

.metric__delta--down {
  color: var(--fs-color-success);
}

.metric__delta--flat {
  color: var(--fs-text-muted);
}

.site-card__traffic {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.site-card__traffic-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--fs-text-muted);
}

.site-card__traffic-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

@media (min-width: 640px) {
  .site-card__traffic-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.traffic-card {
  padding: 10px 8px;
  border-radius: var(--fs-radius-sm);
  background: var(--fs-bg-muted);
  border: 1px solid var(--fs-border);
  text-align: center;
}

.traffic-card--warn {
  border-color: color-mix(in srgb, var(--fs-color-warning) 45%, var(--fs-border));
  background: color-mix(in srgb, var(--fs-color-warning) 10%, var(--fs-bg-muted));
}

.traffic-card--danger {
  border-color: color-mix(in srgb, var(--fs-color-danger) 45%, var(--fs-border));
  background: color-mix(in srgb, var(--fs-color-danger) 10%, var(--fs-bg-muted));
}

.traffic-card__label {
  font-size: 11px;
  color: var(--fs-text-muted);
}

.traffic-card__value {
  margin-top: 4px;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.25;
  color: var(--fs-text-primary);
  font-variant-numeric: tabular-nums;
}

.traffic-card__qps {
  display: block;
  margin-top: 2px;
  font-size: 10px;
  font-weight: 500;
  color: var(--fs-text-secondary);
}

.traffic-card__baseline {
  margin-top: 6px;
  font-size: 10px;
  line-height: 1.35;
  color: var(--fs-text-muted);
}

.traffic-card__baseline-line {
  display: block;
}

.traffic-card__deviation {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  margin-top: 2px;
  color: var(--fs-text-secondary);
}

.traffic-card__deviation-icon {
  font-size: 10px;
}

.traffic-card--warn .traffic-card__deviation {
  color: var(--fs-color-warning);
}

.traffic-card--danger .traffic-card__deviation {
  color: var(--fs-color-danger);
}

.site-card__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  padding-top: 10px;
  border-top: 1px solid var(--fs-border);
}

.site-card__more {
  margin-left: auto;
}

.danger {
  color: var(--fs-color-danger);
}

@media (max-width: 767px) {
  .site-card__meta {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .site-card,
  .metric--clickable {
    transition: none;
  }

  .metric--clickable:hover {
    transform: none;
  }
}
</style>
