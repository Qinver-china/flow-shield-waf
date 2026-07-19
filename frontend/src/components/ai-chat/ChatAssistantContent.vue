<template>
  <div class="chat-assistant">
    <div v-if="steps.length" class="chat-assistant-steps">
      <div
        v-for="step in steps"
        :key="step.id"
        class="chat-assistant-step"
        :class="`chat-assistant-step--${step.status}`"
      >
        <span class="chat-assistant-step-icon">
          <loading-outlined v-if="step.status === 'running'" spin />
          <check-circle-outlined v-else-if="step.status === 'done'" />
          <close-circle-outlined v-else-if="step.status === 'error'" />
          <span v-else class="chat-assistant-step-dot" />
        </span>
        <div class="chat-assistant-step-body">
          <div class="chat-assistant-step-label">{{ step.label }}</div>
          <div v-if="step.detail" class="chat-assistant-step-detail">{{ step.detail }}</div>
        </div>
      </div>
    </div>
    <chat-markdown-content v-if="content" :content="content" />
  </div>
</template>

<script setup lang="ts">
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from "@ant-design/icons-vue";
import ChatMarkdownContent from "@/components/ai-chat/ChatMarkdownContent.vue";
import type { ChatStreamStep } from "@/composables/useAiGuardChat";

withDefaults(
  defineProps<{
    content: string;
    steps?: ChatStreamStep[];
  }>(),
  {
    content: "",
    steps: () => [],
  },
);
</script>

<style scoped>
.chat-assistant {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.chat-assistant-steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--fs-bg-muted) 50%, transparent);
  border: 1px solid color-mix(in srgb, var(--fs-border) 80%, transparent);
}

.chat-assistant-step {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 12px;
  line-height: 1.45;
}

.chat-assistant-step-icon {
  flex-shrink: 0;
  width: 16px;
  margin-top: 1px;
  color: var(--fs-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.chat-assistant-step--running .chat-assistant-step-icon {
  color: var(--fs-color-primary);
}

.chat-assistant-step--done .chat-assistant-step-icon {
  color: #52c41a;
}

.chat-assistant-step--error .chat-assistant-step-icon {
  color: #ff4d4f;
}

.chat-assistant-step-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.chat-assistant-step-body {
  min-width: 0;
  flex: 1;
}

.chat-assistant-step-label {
  color: var(--fs-text-secondary);
  font-weight: 500;
}

.chat-assistant-step--running .chat-assistant-step-label {
  color: var(--fs-text-primary);
}

.chat-assistant-step-detail {
  margin-top: 2px;
  color: var(--fs-text-muted);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow: auto;
}
</style>
