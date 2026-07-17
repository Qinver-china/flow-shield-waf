<template>
  <a-card size="small" title="待确认操作" style="margin: 12px 0">
    <p>AI 建议执行以下操作，确认后将写入系统：</p>
    <a-alert
      v-if="validationError"
      type="error"
      :message="validationError"
      show-icon
      style="margin-bottom: 8px"
    />
    <pre class="payload">{{ JSON.stringify(displayAction, null, 2) }}</pre>
    <rule-draft-preview
      v-if="ruleConditions"
      :conditions="ruleConditions"
    />
    <a-space style="margin-top: 12px">
      <a-button type="primary" :loading="loading" :disabled="!!validationError" @click="confirm(true)">
        确认执行
      </a-button>
      <a-button :loading="loading" @click="confirm(false)">取消</a-button>
    </a-space>
  </a-card>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { api } from "@/api";
import RuleDraftPreview from "./RuleDraftPreview.vue";

const props = defineProps<{
  action: Record<string, unknown>;
  messageId: number | null;
}>();

const emit = defineEmits<{
  confirmed: [];
  cancelled: [];
}>();

const loading = ref(false);

const displayAction = computed(() => {
  if (props.action.actions) return props.action;
  return { tool: props.action.tool, arguments: props.action.arguments };
});

const validationError = computed(() => {
  const preview = (props.action as any).preview;
  if (preview?.error) return String(preview.error);
  if (preview?.valid === false) return "参数校验未通过";
  return null;
});

const ruleConditions = computed(() => {
  const args = (props.action.arguments || {}) as Record<string, unknown>;
  if (props.action.tool === "create_rule" && args.conditions) {
    return args.conditions as Record<string, unknown>;
  }
  return null;
});

async function confirm(approved: boolean) {
  if (!props.messageId) return;
  loading.value = true;
  try {
    await api.post("/api/v1/ai-guard/chat/actions/confirm", {
      message_id: props.messageId,
      approved,
    });
    emit(approved ? "confirmed" : "cancelled");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.payload {
  background: #fafafa;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 160px;
  overflow: auto;
}
</style>
