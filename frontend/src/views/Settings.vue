<template>
  <page-shell title="系统设置" description="按模块管理账户、防护挑战、日志采样、通知与调试选项">
    <a-tabs v-model:activeKey="activeTab" size="large" class="settings-tabs fs-tabs-animated">
      <a-tab-pane key="account" tab="账户安全" />
      <a-tab-pane key="display" tab="显示设置" />
      <a-tab-pane key="challenge" tab="挑战验证" />
      <a-tab-pane key="response-pages" tab="响应页面" />
      <a-tab-pane key="logging" tab="日志采样" />
      <a-tab-pane key="notify" tab="通知通道" />
      <a-tab-pane key="debug" tab="调试模式" />
    </a-tabs>
    <fs-slide-transition :transition-key="activeTab">
      <template v-if="activeTab === 'account'">
<a-card class="settings-panel" :bordered="false">
          <a-row :gutter="[24, 24]">
            <a-col :xs="24" :xl="12">
              <section class="settings-section">
                <div class="section-head">
                  <div class="section-title">修改用户名</div>
                  <div class="section-desc">修改后需使用新用户名登录，系统会自动刷新当前会话凭证。</div>
                </div>
                <a-form layout="vertical" class="section-form">
                  <a-form-item label="当前用户名">
                    <a-input :value="accountProfile.username" disabled />
                  </a-form-item>
                  <a-form-item label="新用户名" required>
                    <a-input
                      v-model:value="usernameForm.new_username"
                      placeholder="3-64 位，支持字母、数字、下划线、连字符"
                      autocomplete="username"
                    />
                  </a-form-item>
                  <a-form-item label="当前密码" required>
                    <a-input-password
                      v-model:value="usernameForm.current_password"
                      placeholder="验证身份"
                      autocomplete="current-password"
                    />
                  </a-form-item>
                  <a-button type="primary" :loading="usernameSaving" @click="saveUsername">
                    保存用户名
                  </a-button>
                </a-form>
              </section>
            </a-col>
            <a-col :xs="24" :xl="12">
              <section class="settings-section">
                <div class="section-head">
                  <div class="section-title">修改密码</div>
                  <div class="section-desc">保存后当前会话仍有效，下次登录请使用新密码。</div>
                </div>
                <a-form layout="vertical" class="section-form">
                  <a-form-item label="当前密码" required>
                    <a-input-password
                      v-model:value="passwordForm.current_password"
                      placeholder="请输入当前密码"
                      autocomplete="current-password"
                    />
                  </a-form-item>
                  <a-form-item label="新密码" required>
                    <a-input-password
                      v-model:value="passwordForm.new_password"
                      placeholder="至少 6 位"
                      autocomplete="new-password"
                    />
                  </a-form-item>
                  <a-form-item label="确认新密码" required>
                    <a-input-password
                      v-model:value="passwordForm.confirm_password"
                      placeholder="再次输入新密码"
                      autocomplete="new-password"
                    />
                  </a-form-item>
                  <a-button type="primary" :loading="passwordSaving" @click="savePassword">
                    保存密码
                  </a-button>
                </a-form>
              </section>
            </a-col>
          </a-row>
        </a-card>
      </template>
      <template v-if="activeTab === 'display'">
<a-card class="settings-panel" :bordered="false">
          <a-form layout="vertical" class="section-form wide">
            <a-form-item label="显示时区">
              <a-select
                v-model:value="displayForm.timezone"
                show-search
                option-filter-prop="label"
                style="width: 100%"
              >
                <a-select-option
                  v-for="opt in displayForm.timezone_options"
                  :key="opt.value"
                  :value="opt.value"
                  :label="opt.label"
                >
                  {{ opt.label }}
                </a-select-option>
              </a-select>
              <div class="hint">
                后台列表、日志、仪表盘等时间将按此时区显示。默认使用中国标准时间（上海，UTC+8）。
              </div>
            </a-form-item>
            <a-form-item label="外网可访问面板地址" required>
              <a-input
                v-model:value="displayForm.panel_public_url"
                placeholder="https://waf.example.com:9000"
              />
              <div class="hint">
                用于 AI 分析邮件中的「应用规则 / 忽略」链接，请勿带尾部斜杠。首次打开本页时会根据当前访问地址自动填入，可手动修改。
              </div>
            </a-form-item>
            <a-form-item>
              <a-button type="primary" :loading="displaySaving" @click="saveDisplay">保存</a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </template>
      <template v-if="activeTab === 'challenge'">
<a-card class="settings-panel" :bordered="false">
          <a-form layout="vertical" class="section-form wide">
            <a-row :gutter="16">
              <a-col :xs="24" :md="12">
                <a-form-item label="JS 挑战免验时间（秒）">
                  <a-input-number
                    v-model:value="form.js_challenge_ttl"
                    :min="60"
                    :max="604800"
                    :step="60"
                    style="width: 100%"
                  />
                  <div class="hint">
                    通过 JS 挑战后，仅对<strong>触发该次挑战的那条规则</strong>及其维度加白。
                  </div>
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="12">
                <a-form-item label="数学/滑动验证免验时间（秒）">
                  <a-input-number
                    v-model:value="form.captcha_ttl"
                    :min="60"
                    :max="604800"
                    :step="60"
                    style="width: 100%"
                  />
                  <div class="hint">
                    通过数学计算或滑动验证后，仅对<strong>触发该次验证的那条规则</strong>加白，默认 1800 秒。
                  </div>
                </a-form-item>
              </a-col>
            </a-row>

            <a-form-item label="免验指纹维度">
              <a-checkbox-group v-model:value="form.clearance_fingerprint_dims" class="dim-group">
                <div v-for="opt in dimensionOptions" :key="opt.key" class="dim-item">
                  <a-checkbox :value="opt.key" :disabled="opt.required">
                    {{ opt.label }}
                  </a-checkbox>
                  <div class="dim-desc">{{ opt.description }}</div>
                </div>
              </a-checkbox-group>
              <div class="hint">
                用于自定义防护规则触发 JS 挑战 / 数学计算 / 滑动验证时的访客识别；限速规则使用其统计维度，不受此项影响。
              </div>
            </a-form-item>

            <a-form-item>
              <a-button type="primary" :loading="saving" @click="save">保存并下发</a-button>
            </a-form-item>
          </a-form>

          <a-alert type="info" show-icon class="tab-notes">
            <template #message>挑战验证说明</template>
            <template #description>
              <ul class="notes">
                <li>免验记录按<strong>规则 + 维度</strong>保存，通过 A 规则不会豁免 B 规则。</li>
                <li>JS 挑战与验证类规则（数学计算、滑动）的免验时间彼此独立。</li>
                <li>修改后立即同步到引擎；引擎重启后免验记录会清空。</li>
              </ul>
            </template>
          </a-alert>
        </a-card>
      </template>
      <template v-if="activeTab === 'response-pages'">
<a-card class="settings-panel" :bordered="false">
          <section class="settings-section page-section">
            <div class="section-head">
              <div class="section-title">全局防护页面</div>
              <div class="section-desc">
                命中拦截动作时返回的完整 HTML 页面，支持变量占位。保存后立即下发到引擎。
              </div>
            </div>
            <a-form layout="vertical" class="section-form wide">
              <a-form-item label="响应状态码">
                <a-select v-model:value="blockPageForm.status_code" style="width: 200px">
                  <a-select-option :value="403">403 Forbidden</a-select-option>
                  <a-select-option :value="429">429 Too Many Requests</a-select-option>
                  <a-select-option :value="451">451 Unavailable For Legal Reasons</a-select-option>
                  <a-select-option :value="503">503 Service Unavailable</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="HTML 内容">
                <a-textarea
                  ref="blockPageTextareaRef"
                  v-model:value="blockPageForm.html"
                  :rows="14"
                  placeholder="输入完整 HTML 页面代码"
                  class="code-textarea"
                />
                <page-template-hints
                  :variables="blockPageForm.template_variables"
                  hint="点击变量标签可插入到光标位置"
                  @insert="(key) => insertVariable(blockPageTextareaRef, blockPageForm, 'html', key)"
                />
              </a-form-item>
              <a-form-item>
                <a-button type="primary" :loading="blockPageSaving" @click="saveBlockPage">
                  保存防护页面
                </a-button>
              </a-form-item>
            </a-form>
          </section>

          <section class="settings-section page-section">
            <div class="section-head">
              <div class="section-title">全局验证页页脚</div>
              <div class="section-desc">
                替换数学计算验证、滑动验证页面底部的品牌说明区域，不影响验证码表单主体。
              </div>
            </div>
            <a-form layout="vertical" class="section-form wide">
              <a-form-item label="页脚 HTML">
                <a-textarea
                  ref="captchaFooterTextareaRef"
                  v-model:value="captchaFooterForm.html"
                  :rows="4"
                  placeholder="例如：由贵站品牌提供安全防护"
                  class="code-textarea"
                />
                <page-template-hints
                  :variables="captchaFooterForm.template_variables"
                  hint="页脚内容会渲染在 .brand 容器内，可包含简单 HTML 标签"
                  @insert="(key) => insertVariable(captchaFooterTextareaRef, captchaFooterForm, 'html', key)"
                />
              </a-form-item>
              <a-form-item>
                <a-button type="primary" :loading="captchaFooterSaving" @click="saveCaptchaFooter">
                  保存页脚代码
                </a-button>
              </a-form-item>
            </a-form>
          </section>
        </a-card>
      </template>
      <template v-if="activeTab === 'logging'">
<a-card class="settings-panel" :bordered="false">
          <a-form layout="vertical" class="section-form wide">
            <a-form-item label="控制模式">
              <a-radio-group v-model:value="logForm.logging_control_mode">
                <a-radio value="manual">手动控制</a-radio>
                <a-radio value="auto_by_traffic">按流量自动启停</a-radio>
              </a-radio-group>
            </a-form-item>

            <template v-if="logForm.logging_control_mode === 'manual'">
              <a-row :gutter="16">
                <a-col :xs="24" :md="12">
                  <a-form-item label="全局日志记录">
                    <a-switch v-model:checked="logForm.logging_enabled" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="12">
                  <a-form-item label="不记录观察模式">
                    <a-switch v-model:checked="logForm.logging_skip_observe" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-row :gutter="16">
                <a-col :xs="24" :md="12">
                  <a-form-item label="无人查看时观察采样率">
                    <a-input-number
                      v-model:value="logForm.observe_sample_rate_idle"
                      :min="0"
                      :max="1"
                      :step="0.01"
                      style="width: 100%"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="12">
                  <a-form-item label="有人查看时观察采样率">
                    <a-input-number
                      v-model:value="logForm.observe_sample_rate_active"
                      :min="0"
                      :max="1"
                      :step="0.01"
                      style="width: 100%"
                    />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-form-item label="拦截类日志写详情">
                <a-switch v-model:checked="logForm.logging_detail_on_block" />
              </a-form-item>
            </template>

            <template v-else>
              <a-alert
                type="info"
                show-icon
                message="流量低于阈值时不记录日志；任一窗口超过阈值时自动开启全部模式（含观察模式）。"
                style="margin-bottom: 16px"
              />
              <div class="threshold-grid">
                <div
                  v-for="th in logForm.logging_auto_thresholds"
                  :key="th.window_sec"
                  class="threshold-item"
                >
                  <div class="threshold-label">{{ windowLabel(th.window_sec) }}</div>
                  <a-input-number v-model:value="th.max_requests" :min="1" style="width: 100%" />
                  <template v-if="trafficBySec[th.window_sec]">
                    <div class="traffic-hint">
                      当前 {{ trafficBySec[th.window_sec].requests }} 次
                      ({{ Number(trafficBySec[th.window_sec].qps || 0).toFixed(1) }} QPS)
                    </div>
                    <a-progress
                      :percent="Math.min(100, Math.round((trafficBySec[th.window_sec].requests / th.max_requests) * 100))"
                      size="small"
                    />
                  </template>
                </div>
              </div>
              <a-row :gutter="16" style="margin-top: 8px">
                <a-col :xs="24" :md="12">
                  <a-form-item label="回落冷却时间（秒）">
                    <a-input-number
                      v-model:value="logForm.logging_auto_cooldown_sec"
                      :min="10"
                      :max="3600"
                      style="width: 100%"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="12">
                  <a-form-item label="自动开启时观察采样率">
                    <a-input-number
                      v-model:value="logForm.logging_auto_observe_sample_rate"
                      :min="0"
                      :max="1"
                      :step="0.01"
                      style="width: 100%"
                    />
                  </a-form-item>
                </a-col>
              </a-row>
            </template>

            <a-form-item label="日志保留天数">
              <a-input-number
                v-model:value="logForm.log_retention_days"
                :min="1"
                :max="365"
                style="width: 100%"
              />
              <div class="traffic-hint">超过该天数的防护日志由 ClickHouse 自动清理（默认 30 天）。</div>
            </a-form-item>

            <a-form-item>
              <a-button type="primary" :loading="logSaving" @click="saveLogging">保存并下发</a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </template>
      <template v-if="activeTab === 'notify'">
<notification-channels-card class="settings-panel notify-panel" />
      </template>
      <template v-if="activeTab === 'debug'">
<a-card class="settings-panel" :bordered="false">
          <a-form layout="vertical" class="section-form wide">
            <a-form-item label="开启调试模式">
              <a-switch v-model:checked="debugForm.debug_mode" />
              <div class="hint">
                开启后，命中防护规则时响应头会附带调试信息，便于在浏览器开发者工具中排查。
                生产环境可能暴露规则信息，建议仅在测试环境使用。
              </div>
            </a-form-item>
            <a-form-item label="限速异常时放行">
              <a-switch v-model:checked="debugForm.ratelimit_fail_open" />
              <div class="hint">
                开启后，限速计数器异常（如共享内存不足）时放行请求，避免误拦全站。
                生产环境建议保持开启；关闭后异常情况下可能批量拦截合法流量。
              </div>
            </a-form-item>
            <a-form-item>
              <div class="debug-headers">
                <div class="debug-headers-title">响应头字段</div>
                <ul>
                  <li><code>X-WAF-Debug</code>：固定为 <code>1</code></li>
                  <li><code>X-WAF-Request-Id</code>：请求 ID</li>
                  <li><code>X-WAF-Rule-Id</code>：命中规则 ID</li>
                  <li><code>X-WAF-Rule-Name</code>：命中规则名称（含中文时为 <code>UTF-8''</code> 百分号编码，可用 <code>decodeURIComponent(value.slice(7))</code> 解码）</li>
                  <li><code>X-WAF-Rule-Source</code>：来源（rule / ratelimit / blacklist）</li>
                  <li><code>X-WAF-Mode</code>：防护方式（observe / block / captcha / js_challenge / slide_captcha）</li>
                </ul>
              </div>
            </a-form-item>
            <a-form-item>
              <a-button type="primary" :loading="debugSaving" @click="saveDebug">保存并下发</a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </template>
    </fs-slide-transition>
  </page-shell>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { message } from "ant-design-vue";
import { api } from "@/api";
import { useAuthStore } from "@/stores/auth";
import { trafficWindowLabels } from "@/views/logs/constants";
import NotificationChannelsCard from "@/components/NotificationChannelsCard.vue";
import FsSlideTransition from "@/components/FsSlideTransition.vue";
import PageShell from "@/components/PageShell.vue";
import PageTemplateHints, { type TemplateVariable } from "@/components/PageTemplateHints.vue";
import { useAppSettingsStore } from "@/stores/appSettings";
import type { TimezoneOption } from "@/stores/appSettings";

const auth = useAuthStore();
const appSettings = useAppSettingsStore();
const activeTab = ref("account");

const accountProfile = reactive({
  username: auth.username || "",
});

const usernameForm = reactive({
  new_username: "",
  current_password: "",
});

const passwordForm = reactive({
  current_password: "",
  new_password: "",
  confirm_password: "",
});

const usernameSaving = ref(false);
const passwordSaving = ref(false);

interface DimensionOption {
  key: string;
  label: string;
  description: string;
  required?: boolean;
}

const form = reactive({
  js_challenge_ttl: 1800,
  captcha_ttl: 1800,
  clearance_fingerprint_dims: ["ip", "ua"] as string[],
});
const dimensionOptions = ref<DimensionOption[]>([]);
const saving = ref(false);
const logSaving = ref(false);
const debugSaving = ref(false);
const displaySaving = ref(false);
const trafficWindows = ref<any[]>([]);
let trafficTimer: ReturnType<typeof setInterval> | null = null;

const logForm = reactive({
  logging_control_mode: "manual",
  logging_enabled: true,
  logging_skip_observe: false,
  observe_sample_rate_idle: 0.01,
  observe_sample_rate_active: 1.0,
  logging_detail_on_block: true,
  logging_auto_thresholds: [
    { window_sec: 10, max_requests: 500 },
    { window_sec: 30, max_requests: 1200 },
    { window_sec: 60, max_requests: 2000 },
    { window_sec: 300, max_requests: 8000 },
    { window_sec: 1800, max_requests: 40000 },
    { window_sec: 3600, max_requests: 80000 },
  ],
  logging_auto_cooldown_sec: 120,
  logging_auto_observe_sample_rate: 1.0,
  log_retention_days: 30,
});

const debugForm = reactive({
  debug_mode: false,
  ratelimit_fail_open: true,
});

const displayForm = reactive<{
  timezone: string;
  timezone_options: TimezoneOption[];
  panel_public_url: string;
}>({
  timezone: "Asia/Shanghai",
  timezone_options: [],
  panel_public_url: "",
});

interface ResponsePageForm {
  status_code?: number;
  html: string;
  template_variables: TemplateVariable[];
}

const blockPageForm = reactive<ResponsePageForm>({
  status_code: 403,
  html: "",
  template_variables: [],
});
const captchaFooterForm = reactive<{ html: string; template_variables: TemplateVariable[] }>({
  html: "",
  template_variables: [],
});
const blockPageTextareaRef = ref<{ $el?: HTMLTextAreaElement; resizableTextArea?: { textArea: HTMLTextAreaElement } } | null>(null);
const captchaFooterTextareaRef = ref<{ $el?: HTMLTextAreaElement; resizableTextArea?: { textArea: HTMLTextAreaElement } } | null>(null);
const blockPageSaving = ref(false);
const captchaFooterSaving = ref(false);

const trafficBySec = computed(() => {
  const map: Record<number, any> = {};
  for (const w of trafficWindows.value) map[w.sec] = w;
  return map;
});

function windowLabel(sec: number) {
  return trafficWindowLabels[sec] || `${sec} 秒`;
}

function startTrafficTimer() {
  if (trafficTimer) return;
  loadTraffic();
  trafficTimer = setInterval(loadTraffic, 5000);
}

function stopTrafficTimer() {
  if (!trafficTimer) return;
  clearInterval(trafficTimer);
  trafficTimer = null;
}

function resetUsernameForm() {
  usernameForm.new_username = "";
  usernameForm.current_password = "";
}

function resetPasswordForm() {
  passwordForm.current_password = "";
  passwordForm.new_password = "";
  passwordForm.confirm_password = "";
}

async function loadAccount() {
  const profile = await auth.fetchProfile();
  accountProfile.username = profile.username;
}

async function saveUsername() {
  const newUsername = usernameForm.new_username.trim();
  if (!newUsername) {
    message.warning("请输入新用户名");
    return;
  }
  if (newUsername.length < 3 || newUsername.length > 64) {
    message.warning("用户名长度需在 3-64 个字符之间");
    return;
  }
  if (!/^[a-zA-Z0-9_-]+$/.test(newUsername)) {
    message.warning("用户名仅允许字母、数字、下划线和连字符");
    return;
  }
  if (!usernameForm.current_password) {
    message.warning("请输入当前密码以验证身份");
    return;
  }
  usernameSaving.value = true;
  try {
    await auth.changeUsername(usernameForm.current_password, newUsername);
    accountProfile.username = auth.username;
    resetUsernameForm();
    message.success("用户名已更新");
  } finally {
    usernameSaving.value = false;
  }
}

async function savePassword() {
  if (!passwordForm.current_password) {
    message.warning("请输入当前密码");
    return;
  }
  if (!passwordForm.new_password) {
    message.warning("请输入新密码");
    return;
  }
  if (passwordForm.new_password.length < 6) {
    message.warning("新密码至少 6 位");
    return;
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    message.warning("两次输入的新密码不一致");
    return;
  }
  passwordSaving.value = true;
  try {
    await auth.changePassword(passwordForm.current_password, passwordForm.new_password);
    resetPasswordForm();
    message.success("密码已更新，请使用新密码登录");
  } finally {
    passwordSaving.value = false;
  }
}

function ensureIpSelected() {
  if (!form.clearance_fingerprint_dims.includes("ip")) {
    form.clearance_fingerprint_dims = ["ip", ...form.clearance_fingerprint_dims];
  }
}

async function load() {
  const resp = await api.get<{
    js_challenge_ttl: number;
    captcha_ttl: number;
    clearance_fingerprint_dims: string[];
    fingerprint_dimension_options: DimensionOption[];
  }>("/api/v1/settings/challenge");
  form.js_challenge_ttl = resp.data.js_challenge_ttl;
  form.captcha_ttl = resp.data.captcha_ttl;
  form.clearance_fingerprint_dims = resp.data.clearance_fingerprint_dims;
  dimensionOptions.value = resp.data.fingerprint_dimension_options;
  ensureIpSelected();
}

async function loadLogging() {
  const resp = await api.get("/api/v1/settings/logging");
  Object.assign(logForm, {
    logging_control_mode: resp.data.logging_control_mode,
    logging_enabled: resp.data.logging_enabled,
    logging_skip_observe: resp.data.logging_skip_observe,
    observe_sample_rate_idle: resp.data.observe_sample_rate_idle,
    observe_sample_rate_active: resp.data.observe_sample_rate_active,
    logging_detail_on_block: resp.data.logging_detail_on_block,
    logging_auto_thresholds: resp.data.logging_auto_thresholds,
    logging_auto_cooldown_sec: resp.data.logging_auto_cooldown_sec,
    logging_auto_observe_sample_rate: resp.data.logging_auto_observe_sample_rate,
    log_retention_days: resp.data.log_retention_days,
  });
}

async function loadDebug() {
  const resp = await api.get<{ debug_mode: boolean; ratelimit_fail_open: boolean }>("/api/v1/settings/debug");
  debugForm.debug_mode = resp.data.debug_mode;
  debugForm.ratelimit_fail_open = resp.data.ratelimit_fail_open ?? true;
}

async function loadDisplay() {
  if (!appSettings.loaded) {
    await appSettings.fetch();
  }
  displayForm.timezone = appSettings.timezone;
  displayForm.timezone_options = appSettings.timezoneOptions;
  displayForm.panel_public_url = appSettings.panelPublicUrl;
}

async function loadBlockPage() {
  const resp = await api.get<ResponsePageForm>("/api/v1/settings/block-page");
  blockPageForm.status_code = resp.data.status_code;
  blockPageForm.html = resp.data.html;
  blockPageForm.template_variables = resp.data.template_variables || [];
}

async function loadCaptchaFooter() {
  const resp = await api.get<{ html: string; template_variables: TemplateVariable[] }>(
    "/api/v1/settings/captcha-footer",
  );
  captchaFooterForm.html = resp.data.html;
  captchaFooterForm.template_variables = resp.data.template_variables || [];
}

function textareaElement(
  refObj: { value: { $el?: HTMLTextAreaElement; resizableTextArea?: { textArea: HTMLTextAreaElement } } | null },
) {
  const comp = refObj.value;
  if (!comp) return null;
  return comp.resizableTextArea?.textArea || comp.$el;
}

function insertVariable(
  refObj: { value: { $el?: HTMLTextAreaElement; resizableTextArea?: { textArea: HTMLTextAreaElement } } | null },
  target: { html: string },
  field: "html",
  key: string,
) {
  const token = `{${key}}`;
  const el = textareaElement(refObj);
  if (!el) {
    target[field] += token;
    return;
  }
  const start = el.selectionStart ?? target[field].length;
  const end = el.selectionEnd ?? start;
  const value = target[field];
  target[field] = value.slice(0, start) + token + value.slice(end);
  const pos = start + token.length;
  requestAnimationFrame(() => {
    el.focus();
    el.setSelectionRange(pos, pos);
  });
}

async function saveBlockPage() {
  if (!blockPageForm.html.trim()) {
    message.warning("请输入防护页面 HTML");
    return;
  }
  blockPageSaving.value = true;
  try {
    await api.put("/api/v1/settings/block-page", {
      status_code: blockPageForm.status_code,
      html: blockPageForm.html,
    });
    message.success("防护页面已保存并下发");
  } finally {
    blockPageSaving.value = false;
  }
}

async function saveCaptchaFooter() {
  if (!captchaFooterForm.html.trim()) {
    message.warning("请输入页脚 HTML");
    return;
  }
  captchaFooterSaving.value = true;
  try {
    await api.put("/api/v1/settings/captcha-footer", {
      html: captchaFooterForm.html,
    });
    message.success("验证页页脚已保存并下发");
  } finally {
    captchaFooterSaving.value = false;
  }
}

async function loadTraffic() {
  const resp = await api.get("/api/v1/traffic/stats");
  trafficWindows.value = resp.data.global?.windows || [];
}

async function saveLogging() {
  logSaving.value = true;
  try {
    await api.put("/api/v1/settings/logging", { ...logForm });
    message.success("日志设置已保存并下发");
  } finally {
    logSaving.value = false;
  }
}

async function save() {
  ensureIpSelected();
  if (form.clearance_fingerprint_dims.length === 0) {
    message.error("请至少选择一个指纹维度");
    return;
  }
  saving.value = true;
  try {
    await api.put("/api/v1/settings/challenge", {
      js_challenge_ttl: form.js_challenge_ttl,
      captcha_ttl: form.captcha_ttl,
      clearance_fingerprint_dims: form.clearance_fingerprint_dims,
    });
    message.success("设置已保存并下发到引擎");
  } finally {
    saving.value = false;
  }
}

async function saveDebug() {
  debugSaving.value = true;
  try {
    await api.put("/api/v1/settings/debug", {
      debug_mode: debugForm.debug_mode,
      ratelimit_fail_open: debugForm.ratelimit_fail_open,
    });
    message.success("调试模式已保存并下发");
  } finally {
    debugSaving.value = false;
  }
}

async function saveDisplay() {
  const url = displayForm.panel_public_url.trim().replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(url)) {
    message.warning("面板地址必须以 http:// 或 https:// 开头");
    return;
  }
  displaySaving.value = true;
  try {
    await appSettings.updateDisplay({
      timezone: displayForm.timezone,
      panel_public_url: url,
    });
    displayForm.timezone = appSettings.timezone;
    displayForm.timezone_options = appSettings.timezoneOptions;
    displayForm.panel_public_url = appSettings.panelPublicUrl;
    message.success("显示设置已保存");
  } finally {
    displaySaving.value = false;
  }
}

watch(activeTab, (tab) => {
  if (tab === "logging") startTrafficTimer();
  else stopTrafficTimer();
});

onMounted(async () => {
  await loadAccount();
  await load();
  await loadLogging();
  await loadDebug();
  await loadDisplay();
  await loadBlockPage();
  await loadCaptchaFooter();
  if (activeTab.value === "logging") startTrafficTimer();
});

onUnmounted(() => {
  stopTrafficTimer();
});
</script>

<style scoped>
.settings-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 12px;
}

.settings-panel {
  background: var(--fs-bg-surface);
  border-radius: var(--fs-radius-md);
  box-shadow: var(--fs-shadow-sm);
  border: 1px solid var(--fs-border);
}

.settings-panel :deep(.ant-card-body) {
  padding: 20px 24px;
}

.notify-panel {
  margin-top: 0 !important;
}

.settings-section {
  height: 100%;
  padding: 16px;
  border: 1px solid #7d7d7d1f;
  border-radius: 10px;
  background: #8585850a;
}

.section-head {
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
}

.section-desc {
  margin-top: 4px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.section-form {
  max-width: 420px;
}

.section-form.wide {
  max-width: 760px;
}

.hint {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.dim-group {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
  width: 100%;
}

.dim-item {
  padding: 10px 12px;
  border-radius: 8px;
  background: #818da30a;
}

.dim-desc {
  margin-top: 4px;
  margin-left: 24px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.threshold-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 8px;
}

.threshold-item {
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.threshold-label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
}

.traffic-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
}

.tab-notes {
  margin-top: 8px;
}

.notes {
  margin: 0;
  padding-left: 18px;
  color: #475569;
  line-height: 1.7;
}

.debug-headers {
  padding: 12px 14px;
  border-radius: 8px;
  background: #6767670d;
}

.debug-headers-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
}

.debug-headers ul {
  margin: 0;
  padding-left: 18px;
  color: #475569;
  font-size: 13px;
  line-height: 1.8;
}

.debug-headers code {
  font-size: 12px;
}

.page-section + .page-section {
  margin-top: 16px;
}

.code-textarea :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
}
</style>
