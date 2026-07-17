<template>
  <div class="chat-layout">
    <div class="chat-side">
      <a-button type="dashed" block style="margin-bottom: 8px" @click="newSession">新对话</a-button>
      <a-list size="small" :data-source="sessions" :loading="sessionsLoading">
        <template #renderItem="{ item }">
          <a-list-item
            class="session-item"
            :class="{ active: item.id === sessionId }"
            @click="openSession(item.id)"
          >
            {{ item.title }}
          </a-list-item>
        </template>
      </a-list>
    </div>
    <div class="chat-main">
      <chat-message-list :messages="messages" />
      <pending-action-card
        v-if="pendingAction"
        :action="pendingAction"
        :message-id="pendingMessageId"
        @confirmed="onActionDone"
        @cancelled="pendingAction = null"
      />
      <div class="chat-input">
        <a-textarea
          v-model:value="input"
          :rows="3"
          placeholder="例如：为 example.com 创建一条防 SQL 注入的观察规则"
          @keydown.ctrl.enter="send"
        />
        <a-button type="primary" :loading="sending" style="margin-top: 8px" @click="send">
          发送 (Ctrl+Enter)
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { message } from "ant-design-vue";
import { onMounted, ref } from "vue";
import { api } from "@/api";
import ChatMessageList from "../components/ChatMessageList.vue";
import PendingActionCard from "../components/PendingActionCard.vue";

interface ChatMsg {
  id?: number;
  role: string;
  content: string;
  pending_action?: Record<string, unknown> | null;
  action_status?: string | null;
}

const sessions = ref<{ id: number; title: string }[]>([]);
const sessionsLoading = ref(false);
const sessionId = ref<number | null>(null);
const messages = ref<ChatMsg[]>([]);
const input = ref("");
const sending = ref(false);
const pendingAction = ref<Record<string, unknown> | null>(null);
const pendingMessageId = ref<number | null>(null);

async function loadSessions() {
  sessionsLoading.value = true;
  try {
    const res = await api.get("/api/v1/ai-guard/chat/sessions");
    sessions.value = res.data || [];
  } finally {
    sessionsLoading.value = false;
  }
}

async function loadMessages(id: number) {
  const res = await api.get(`/api/v1/ai-guard/chat/sessions/${id}/messages`);
  messages.value = res.data || [];
  const pending = [...messages.value].reverse().find(
    (m) => m.pending_action && m.action_status === "pending",
  );
  pendingAction.value = pending?.pending_action || null;
  pendingMessageId.value = pending?.id || null;
}

function newSession() {
  sessionId.value = null;
  messages.value = [];
  pendingAction.value = null;
  pendingMessageId.value = null;
}

async function openSession(id: number) {
  sessionId.value = id;
  await loadMessages(id);
}

async function send() {
  const text = input.value.trim();
  if (!text || sending.value) return;
  sending.value = true;
  messages.value.push({ role: "user", content: text });
  input.value = "";
  const assistantIdx = messages.value.length;
  messages.value.push({ role: "assistant", content: "" });

  try {
    const token = localStorage.getItem("waf_access_token");
    const resp = await fetch("/api/v1/ai-guard/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ session_id: sessionId.value, message: text }),
    });
    if (!resp.ok) {
      if (resp.status === 401) {
        localStorage.removeItem("waf_access_token");
        location.href = "/login";
        return;
      }
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.message || "请求失败");
    }
    const reader = resp.body?.getReader();
    if (!reader) throw new Error("无法读取响应流");
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") continue;
        const parsed = JSON.parse(raw);
        if (parsed.type === "error") throw new Error(parsed.message);
        if (parsed.type === "session") sessionId.value = parsed.session_id;
        if (parsed.type === "delta") {
          messages.value[assistantIdx].content += parsed.delta;
        }
        if (parsed.type === "done") {
          messages.value[assistantIdx].id = parsed.message_id;
          if (parsed.pending_action) {
            pendingAction.value = parsed.pending_action;
            pendingMessageId.value = parsed.message_id;
          }
        }
      }
    }
    await loadSessions();
  } catch (e: any) {
    messages.value.splice(assistantIdx, 1);
    if (messages.value[messages.value.length - 1]?.role === "user") {
      messages.value.pop();
      input.value = text;
    }
    message.error(e?.message || "发送失败");
  } finally {
    sending.value = false;
  }
}

function onActionDone() {
  pendingAction.value = null;
  if (sessionId.value) loadMessages(sessionId.value);
  message.success("操作已处理");
}

onMounted(loadSessions);
</script>

<style scoped>
.chat-layout {
  display: flex;
  gap: 16px;
  min-height: 520px;
}
.chat-side {
  width: 200px;
  flex-shrink: 0;
}
.session-item {
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--fs-radius-sm);
  transition: background var(--fs-transition);
}
.session-item.active {
  background: color-mix(in srgb, var(--fs-color-primary) 12%, var(--fs-bg-surface));
  color: var(--fs-color-primary);
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-input {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--fs-border);
}

@media (max-width: 767px) {
  .chat-layout {
    flex-direction: column;
    min-height: auto;
  }

  .chat-side {
    width: 100%;
    max-height: 160px;
    overflow: auto;
  }
}
</style>
