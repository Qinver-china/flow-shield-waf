<template>
  <div class="settings-group" :class="{ 'is-loading': loading }">
    <a-card class="settings-panel" :bordered="false" :loading="loading">
      <div class="section-head">
        <div class="section-title">功能开关</div>
        <div class="section-desc">控制 AI 防护、智能助手与自动化防护是否启用。</div>
      </div>
      <div class="switch-stack">
        <settings-switch-row
          v-model:checked="form.enabled"
          title="启用 AI 防护"
          description="关闭后，AI 助手、自动分析与悬浮入口将一并停用。"
        />
        <settings-switch-row
          v-model:checked="form.chat_enabled"
          title="启用智能聊天"
          description="允许在 AI 防护页与悬浮窗口中使用对话助手。"
          :disabled="!form.enabled"
        />
        <settings-switch-row
          v-model:checked="form.floating_chat_enabled"
          title="显示悬浮 AI 助手"
          description="关闭后，页面右下角不再显示 AI 圆形按钮与悬浮聊天窗口。"
          :disabled="!form.enabled || !form.chat_enabled"
        />
        <settings-switch-row
          v-model:checked="form.defense_enabled"
          title="启用自动化防护"
          description="按防护策略自动拉取日志并由 AI 分析、生成或应用规则。"
          :disabled="!form.enabled"
        />
        <settings-switch-row
          v-model:checked="form.defense_web_search_enabled"
          title="允许自动防护联网搜索"
          description="开启后，AI 可将脱敏搜索词发送至第三方公开搜索服务。外部内容可能不准确或含提示词注入，请仅在接受数据外发与自动决策风险时启用。"
          warning
          :disabled="!form.enabled || !form.defense_enabled"
        />
      </div>
    </a-card>

    <a-card class="settings-panel" :bordered="false" :loading="loading">
      <div class="section-head section-head--row">
        <div>
          <div class="section-title">模型连接</div>
          <div class="section-desc">OpenAI 兼容 API 地址、密钥与默认模型。</div>
        </div>
        <a-button :loading="testing" :disabled="loading" @click="testConn">测试连接</a-button>
      </div>
      <a-form layout="vertical" class="section-form wide">
        <a-form-item label="API Base URL">
          <a-input
            v-model:value="form.provider_base_url"
            type="url"
            inputmode="url"
            placeholder="https://api.openai.com/v1"
            :disabled="!form.enabled"
          />
        </a-form-item>
        <a-form-item label="API Key">
          <a-input-password
            v-model:value="form.api_key"
            :placeholder="form.api_key_set ? '已配置（留空不修改）' : 'sk-...'"
            :disabled="!form.enabled"
          />
        </a-form-item>
        <a-form-item label="模型">
          <div class="model-field">
            <a-auto-complete
              v-model:value="form.model"
              :options="modelOptions"
              placeholder="gpt-4o-mini"
              class="model-field__input"
              :filter-option="filterModel"
              :disabled="!form.enabled"
            />
            <a-button :loading="loadingModels" :disabled="!form.enabled" @click="loadModels">
              拉取模型
            </a-button>
          </div>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card class="settings-panel" :bordered="false" :loading="loading">
      <div class="section-head">
        <div class="section-title">生成参数</div>
        <div class="section-desc">影响对话与自动分析时的随机性与输出长度上限。</div>
      </div>
      <a-form layout="vertical" class="section-form wide">
        <a-row :gutter="16">
          <a-col :xs="24" :md="12">
            <a-form-item label="Temperature">
              <preset-number-field
                v-model="form.temperature"
                :presets="temperaturePresets"
                :min="0"
                :max="2"
                :step="0.1"
                :precision="1"
                show-slider
              />
              <div class="hint">较低更稳定，较高更有创造性，建议 0.2–0.5</div>
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="12">
            <a-form-item label="Max Tokens">
              <preset-number-field
                v-model="form.max_tokens"
                :presets="maxTokensPresets"
                :min="256"
                :max="128000"
                :step="256"
                show-slider
              />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <a-card class="settings-panel" :bordered="false" :loading="loading">
      <div class="section-head">
        <div class="section-title">自动防护</div>
        <div class="section-desc">全局默认的应用模式、分析配额与置信度门槛。</div>
      </div>
      <a-form layout="vertical" class="section-form wide">
        <a-form-item label="默认规则应用模式">
          <a-segmented
            v-model:value="form.default_apply_mode"
            :options="applyModeOptions"
            class="mode-segmented"
            :disabled="!form.enabled || !form.defense_enabled"
          />
          <div class="hint">
            「自动分析并处理」由 AI 在观察、拦截、JS 挑战、滑动验证中选择动作；非观察动作须达到下方最低置信度，否则降为观察。
          </div>
        </a-form-item>
        <a-row :gutter="16">
          <a-col :xs="24" :md="12">
            <a-form-item label="单次分析日志上限">
              <preset-number-field
                v-model="form.max_logs_per_analysis"
                :presets="maxLogsPresets"
                :min="10"
                :max="2000"
                unit="条"
              />
            </a-form-item>
          </a-col>
          <a-col :xs="24" :md="12">
            <a-form-item label="分析冷却时间">
              <duration-field
                v-model="form.analysis_cooldown_sec"
                :min-seconds="30"
                :max-seconds="86400"
                :units="['second', 'minute']"
                :quick-presets="cooldownPresets"
              />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="非观察动作最低置信度">
          <preset-number-field
            v-model="confidencePercent"
            :presets="confidencePresets"
            :min="50"
            :max="100"
            unit="%"
            show-slider
          />
          <div class="hint">
            自动分析并处理时，拦截 / JS 挑战 / 滑动验证须达到该置信度，否则改为观察。
          </div>
        </a-form-item>
      </a-form>
    </a-card>

    <settings-save-bar :dirty="dirty" :loading="saving" label="保存" @save="save" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { message } from "ant-design-vue";
import { api } from "@/api";
import DurationField from "@/components/settings/DurationField.vue";
import PresetNumberField from "@/components/settings/PresetNumberField.vue";
import SettingsSaveBar from "@/components/settings/SettingsSaveBar.vue";
import SettingsSwitchRow from "@/components/settings/SettingsSwitchRow.vue";
import { useFloatingAiChatStore } from "@/stores/floatingAiChat";

const floatingAi = useFloatingAiChatStore();
const loading = ref(false);
const saving = ref(false);
const testing = ref(false);
const loadingModels = ref(false);
const modelOptions = ref<{ label: string; value: string }[]>([]);
const snapshotValue = ref("");

const temperaturePresets = [
  { value: 0.2, label: "0.2" },
  { value: 0.3, label: "0.3" },
  { value: 0.5, label: "0.5" },
  { value: 0.7, label: "0.7" },
];

const maxTokensPresets = [
  { value: 2048, label: "2048" },
  { value: 4096, label: "4096" },
  { value: 8192, label: "8192" },
  { value: 16384, label: "16384" },
];

const maxLogsPresets = [
  { value: 50, label: "50 条" },
  { value: 100, label: "100 条" },
  { value: 200, label: "200 条" },
  { value: 500, label: "500 条" },
];

const confidencePresets = [
  { value: 70, label: "70%" },
  { value: 80, label: "80%" },
  { value: 85, label: "85%" },
  { value: 90, label: "90%" },
  { value: 95, label: "95%" },
];

const cooldownPresets = [
  { seconds: 30, label: "30 秒" },
  { seconds: 120, label: "2 分钟" },
  { seconds: 300, label: "5 分钟" },
  { seconds: 600, label: "10 分钟" },
];

const applyModeOptions = [
  { value: "suggest_only", label: "仅生成建议" },
  { value: "auto_observe", label: "自动观察" },
  { value: "auto_handle", label: "自动处理" },
];

const form = reactive({
  enabled: false,
  provider_base_url: "https://api.openai.com/v1",
  api_key: "",
  api_key_set: false,
  model: "gpt-4o-mini",
  temperature: 0.3,
  max_tokens: 4096,
  chat_enabled: true,
  floating_chat_enabled: true,
  defense_enabled: true,
  defense_web_search_enabled: false,
  default_apply_mode: "auto_handle",
  max_logs_per_analysis: 200,
  analysis_cooldown_sec: 300,
  auto_block_min_confidence: 0.85,
});

function snapshot() {
  const { api_key_set, ...rest } = form;
  return JSON.stringify(rest);
}

function refreshSnapshot() {
  snapshotValue.value = snapshot();
}

const dirty = computed(() => snapshot() !== snapshotValue.value);

const confidencePercent = computed({
  get: () => Math.round(form.auto_block_min_confidence * 100),
  set: (value: number) => {
    form.auto_block_min_confidence = value / 100;
  },
});

async function load() {
  loading.value = true;
  try {
    const res = await api.get("/api/v1/ai-guard/settings");
    Object.assign(form, res.data);
    form.api_key = "";
    form.floating_chat_enabled = res.data.floating_chat_enabled !== false;
    floatingAi.setFabEnabled(form.enabled && form.floating_chat_enabled);
    refreshSnapshot();
  } finally {
    loading.value = false;
  }
}

function filterModel(input: string, option: { value: string }) {
  return option.value.toLowerCase().includes(input.toLowerCase());
}

async function loadModels() {
  loadingModels.value = true;
  try {
    const res = await api.get<{ models: string[] }>("/api/v1/ai-guard/settings/models");
    modelOptions.value = (res.data.models || []).map((m) => ({ label: m, value: m }));
    if (modelOptions.value.length) {
      message.success(`已获取 ${modelOptions.value.length} 个可用模型`);
      if (!form.model && modelOptions.value[0]) {
        form.model = modelOptions.value[0].value;
      }
    } else {
      message.warning("未获取到可用模型");
    }
  } finally {
    loadingModels.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    const payload: Record<string, unknown> = { ...form };
    if (!payload.api_key) delete payload.api_key;
    delete payload.api_key_set;
    await api.put("/api/v1/ai-guard/settings", payload);
    floatingAi.setFabEnabled(form.enabled && form.floating_chat_enabled);
    message.success("已保存");
    await load();
  } finally {
    saving.value = false;
  }
}

async function testConn() {
  testing.value = true;
  try {
    const res = await api.post("/api/v1/ai-guard/settings/test");
    message.success(`连接成功：${res.data.reply}`);
  } finally {
    testing.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.settings-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 8px;
  max-width: 860px;
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

.section-head {
  margin-bottom: 16px;
}

.section-head--row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
}

.section-desc {
  margin-top: 4px;
  font-size: 13px;
  color: var(--fs-text-secondary);
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
  color: var(--fs-text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.switch-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.model-field {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.model-field__input {
  flex: 1;
  min-width: 200px;
}

.mode-segmented {
  max-width: 100%;
}

@media (max-width: 767px) {
  .mode-segmented :deep(.ant-segmented) {
    flex-wrap: wrap;
  }

  .section-head--row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
