<template>
  <div class="messages">
    <div v-for="(msg, i) in messages" :key="i" class="msg-row" :class="msg.role">
      <div class="bubble">
        <div class="role">{{ roleLabel(msg.role) }}</div>
        <div class="content">{{ msg.content }}</div>
      </div>
    </div>
    <a-empty v-if="!messages.length" description="开始与 AI 助手对话" />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  messages: { role: string; content: string }[];
}>();

function roleLabel(role: string) {
  if (role === "user") return "你";
  if (role === "assistant") return "AI";
  return role;
}
</script>

<style scoped>
.messages {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
  padding: 8px 0;
}

.msg-row {
  display: flex;
  margin-bottom: 12px;
}

.msg-row.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: var(--fs-radius-md);
  background: var(--fs-bg-muted);
  border: 1px solid var(--fs-border);
}

.msg-row.user .bubble {
  background: color-mix(in srgb, var(--fs-color-primary) 10%, var(--fs-bg-surface));
  border-color: color-mix(in srgb, var(--fs-color-primary) 25%, var(--fs-border));
}

.role {
  font-size: 12px;
  color: var(--fs-text-muted);
  margin-bottom: 4px;
}

.content {
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--fs-text-primary);
}

@media (max-width: 767px) {
  .messages {
    max-height: 320px;
  }

  .bubble {
    max-width: 95%;
  }
}
</style>
