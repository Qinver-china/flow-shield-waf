<template>
  <a-card title="AI 模型配置" :loading="loading">
    <a-form layout="vertical" style="max-width: 640px">
      <a-form-item label="启用 AI 防护">
        <a-switch v-model:checked="form.enabled" />
      </a-form-item>
      <a-form-item label="API Base URL">
        <a-input v-model:value="form.provider_base_url" placeholder="https://api.openai.com/v1" />
      </a-form-item>
      <a-form-item label="API Key">
        <a-input-password
          v-model:value="form.api_key"
          :placeholder="form.api_key_set ? '已配置（留空不修改）' : 'sk-...'"
        />
      </a-form-item>
      <a-form-item label="模型">
        <a-space style="width: 100%">
          <a-auto-complete
            v-model:value="form.model"
            :options="modelOptions"
            placeholder="gpt-5.4-mini"
            style="width: 420px"
            :filter-option="filterModel"
          />
          <a-button :loading="loadingModels" @click="loadModels">拉取模型</a-button>
        </a-space>
      </a-form-item>
      <a-row :gutter="12">
        <a-col :span="12">
          <a-form-item label="Temperature">
            <a-input-number v-model:value="form.temperature" :min="0" :max="2" :step="0.1" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="Max Tokens">
            <a-input-number v-model:value="form.max_tokens" :min="256" :max="128000" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>
      <a-form-item label="启用智能聊天">
        <a-switch v-model:checked="form.chat_enabled" />
      </a-form-item>
      <a-form-item label="显示悬浮 AI 助手">
        <a-switch v-model:checked="form.floating_chat_enabled" />
        <div class="hint">关闭后，页面右下角将不再显示 AI 圆形按钮与悬浮聊天窗口。</div>
      </a-form-item>
      <a-form-item label="启用自动化防护">
        <a-switch v-model:checked="form.defense_enabled" />
      </a-form-item>
      <a-form-item label="允许自动防护联网搜索">
        <a-switch v-model:checked="form.defense_web_search_enabled" />
        <div class="hint warning-hint">
          开启后，AI 自动防护可将脱敏后的搜索词发送至第三方公开搜索服务。外部内容可能不准确或包含提示词注入，请仅在接受数据外发与自动决策风险时启用。
        </div>
      </a-form-item>
      <a-form-item label="默认规则应用模式">
        <a-select v-model:value="form.default_apply_mode">
          <a-select-option value="suggest_only">仅生成建议</a-select-option>
          <a-select-option value="auto_observe">自动创建（观察）</a-select-option>
          <a-select-option value="auto_handle">自动分析并处理</a-select-option>
        </a-select>
        <div class="hint">
          「自动分析并处理」由 AI 在观察、拦截、JS 挑战、滑动验证中选择动作；非观察动作需达到下方最低置信度，否则降为观察。旧选项「自动创建拦截」已并入本模式。
        </div>
      </a-form-item>
      <a-row :gutter="12">
        <a-col :span="12">
          <a-form-item label="单次分析日志上限">
            <a-input-number v-model:value="form.max_logs_per_analysis" :min="10" :max="2000" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="分析冷却（秒）">
            <a-input-number v-model:value="form.analysis_cooldown_sec" :min="30" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>
      <a-form-item label="非观察动作最低置信度">
        <a-slider v-model:value="form.auto_block_min_confidence" :min="0.5" :max="1" :step="0.05" />
        <div class="hint">自动分析并处理时，拦截 / JS 挑战 / 滑动验证须达到该置信度，否则改为观察。</div>
      </a-form-item>
      <a-space>
        <a-button type="primary" :loading="saving" @click="save">保存配置</a-button>
        <a-button :loading="testing" @click="testConn">测试连接</a-button>
      </a-space>
    </a-form>
  </a-card>
</template>

<script setup lang="ts">
import { message } from "ant-design-vue";
import { onMounted, reactive, ref } from "vue";
import { api } from "@/api";
import { useFloatingAiChatStore } from "@/stores/floatingAiChat";

const floatingAi = useFloatingAiChatStore();
const loading = ref(false);
const saving = ref(false);
const testing = ref(false);
const loadingModels = ref(false);
const modelOptions = ref<{ label: string; value: string }[]>([]);

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

async function load() {
  loading.value = true;
  try {
    const res = await api.get("/api/v1/ai-guard/settings");
    Object.assign(form, res.data);
    form.api_key = "";
    form.floating_chat_enabled = res.data.floating_chat_enabled !== false;
    floatingAi.setFabEnabled(form.enabled && form.floating_chat_enabled);
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
.hint {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.warning-hint {
  color: #d97706;
}
</style>
