<template>
  <x-provider>
    <div
      class="ai-chat-panel"
      :class="{
        'ai-chat-panel--embedded': embedded,
        'ai-chat-panel--compact': compact,
        'ai-chat-panel--sider-collapsed': effectiveCollapsibleSider && !siderVisible,
      }"
    >
      <div
        v-if="effectiveCollapsibleSider && siderVisible"
        class="ai-chat-sider-backdrop"
        @click="siderVisible = false"
      />

      <aside
        v-show="!effectiveCollapsibleSider || siderVisible"
        class="ai-chat-sider"
        :class="{ 'ai-chat-sider--overlay': effectiveCollapsibleSider }"
      >
        <div class="ai-chat-sider-head">
          <div class="ai-chat-logo">
            <app-logo variant="square" :show-text="false" :collapsed="false" />
            <div class="ai-chat-logo-text">
              <strong>{{ BRAND.name }}</strong>
              <span>AI智能助手</span>
            </div>
          </div>
          <a-button
            v-if="effectiveCollapsibleSider"
            type="text"
            size="small"
            class="ai-chat-sider-close"
            aria-label="收起会话列表"
            @click="siderVisible = false"
          >
            <menu-fold-outlined />
          </a-button>
        </div>

        <a-button
          type="dashed"
          block
          class="ai-chat-new-btn"
          :disabled="sending"
          @click="onNewSession"
        >
          <template #icon><plus-outlined /></template>
          新对话
        </a-button>

        <a-spin :spinning="sessionsLoading" class="ai-chat-sessions-spin">
          <conversations
            class="ai-chat-conversations"
            :items="conversationItems"
            :active-key="activeConversationKey"
            :menu="conversationMenu"
            groupable
            :styles="{ item: { padding: '0 8px' } }"
            @active-change="onConversationSelect"
          />
        </a-spin>

        <a-button
          type="text"
          danger
          block
          class="ai-chat-clear-all-btn"
          :disabled="sending || !sessions.length"
          @click="clearAllSessions"
        >
          清空所有对话
        </a-button>
      </aside>

      <section class="ai-chat-main">
        <div v-if="effectiveCollapsibleSider" class="ai-chat-toolbar">
          <a-tooltip title="会话列表">
            <a-button type="text" class="ai-chat-toolbar-btn" @click="siderVisible = true">
              <unordered-list-outlined />
            </a-button>
          </a-tooltip>
          <a-tooltip title="新对话">
            <a-button type="text" class="ai-chat-toolbar-btn" @click="onNewSession">
              <plus-outlined />
            </a-button>
          </a-tooltip>
          <span class="ai-chat-toolbar-title">AI 智能助手</span>
        </div>

        <div class="ai-chat-list">
          <div
            v-if="messages.length"
            :key="messageListKey"
            class="ai-chat-bubbles"
          >
            <div
              v-for="item in bubbleItems"
              :key="item.key"
              class="ai-chat-msg"
              :class="`ai-chat-msg--${item.role}`"
            >
              <div class="ai-chat-msg-stack">
                <div class="ai-chat-msg-bubble">
                  <a-spin v-if="item.loading" size="small" />
                  <chat-assistant-content
                    v-else-if="item.role === 'assistant'"
                    :content="String(item.content || '')"
                    :steps="item.steps"
                  />
                  <chat-markdown-content
                    v-else
                    :content="String(item.content || '')"
                  />
                </div>

                <pending-action-card
                  v-if="item.action_status === 'pending' && item.pending_action"
                  class="ai-chat-pending"
                  :action="item.pending_action"
                  :message-id="item.messageId"
                  @confirmed="onActionDone"
                  @cancelled="clearPending"
                />
                <div
                  v-else-if="item.action_status === 'executed'"
                  class="ai-chat-action-result ai-chat-action-result--executed"
                >
                  已确认执行该操作
                </div>
                <div
                  v-else-if="item.action_status === 'cancelled'"
                  class="ai-chat-action-result ai-chat-action-result--cancelled"
                >
                  已取消执行该操作
                </div>
              </div>
            </div>
          </div>
          <div v-else class="ai-chat-welcome">
            <welcome
              variant="borderless"
              :icon="welcomeIcon"
              title="你好，我是流盾 AI 助手"
              description="可帮你查询日志、分析攻击、生成防护规则与 CC 策略。建议先生成观察规则，确认无误后再拦截。"
            />
            <div class="ai-chat-prompt-grid">
              <prompts
                :items="welcomePrompts"
                wrap
                @item-click="onPromptClick"
              />
            </div>
          </div>
        </div>

        <div class="ai-chat-sender-wrap">
          <prompts
            v-if="!messages.length"
            class="ai-chat-sender-prompts"
            :items="senderPrompts"
            wrap
            @item-click="onPromptClick"
          />
          <sender
            v-model:value="input"
            class="ai-chat-sender"
            :loading="sending"
            placeholder="描述你的需求，例如：生成防 XSS 观察规则"
            @submit="send()"
          />
        </div>
      </section>
    </div>
  </x-provider>
</template>

<script setup lang="ts">
import { computed, h, ref, watch } from "vue";
import {
  MenuFoldOutlined,
  PlusOutlined,
  UnorderedListOutlined,
} from "@ant-design/icons-vue";
import {
  Conversations,
  Prompts,
  Sender,
  Welcome,
  XProvider,
} from "ant-design-x-vue";
import AppLogo from "@/components/AppLogo.vue";
import ChatAssistantContent from "@/components/ai-chat/ChatAssistantContent.vue";
import ChatMarkdownContent from "@/components/ai-chat/ChatMarkdownContent.vue";
import PendingActionCard from "@/views/ai-guard/components/PendingActionCard.vue";
import { useAiGuardChat } from "@/composables/useAiGuardChat";
import { useBreakpoint } from "@/composables/useBreakpoint";
import { BRAND } from "@/constants/brand";
import { useFloatingAiChatStore } from "@/stores/floatingAiChat";

const props = withDefaults(
  defineProps<{
    embedded?: boolean;
    compact?: boolean;
    autoLoadSessions?: boolean;
    collapsibleSider?: boolean;
  }>(),
  {
    embedded: false,
    compact: false,
    autoLoadSessions: true,
    collapsibleSider: false,
  },
);

const siderVisible = ref(true);
const floatingStore = useFloatingAiChatStore();
const { width } = useBreakpoint();

const isNarrowLayout = computed(() => width.value <= 900);
const effectiveCollapsibleSider = computed(
  () => props.collapsibleSider || (props.embedded && isNarrowLayout.value),
);

watch(
  effectiveCollapsibleSider,
  (collapsible) => {
    siderVisible.value = !collapsible;
  },
  { immediate: true },
);

const welcomeIcon = () =>
  h("img", {
    src: BRAND.logoSquare,
    alt: BRAND.name,
    style: "width: 48px; height: 48px; border-radius: 12px;",
  });

const {
  sessions,
  sessionsLoading,
  input,
  sending,
  messages,
  conversationItems,
  activeConversationKey,
  bubbleItems,
  messageListKey,
  welcomePrompts,
  senderPrompts,
  conversationMenu,
  newSession,
  clearAllSessions,
  onConversationChange,
  send,
  onActionDone,
  onPromptClick,
  clearPending,
} = useAiGuardChat({
  autoLoadSessions: props.autoLoadSessions,
  restoreLatestSession: props.autoLoadSessions !== false,
  getPreferredSessionId: () => floatingStore.lastSessionId,
  onSessionIdChange: (id) => {
    floatingStore.setLastSessionId(id);
  },
});

function onNewSession() {
  newSession();
  if (effectiveCollapsibleSider.value) {
    siderVisible.value = false;
  }
}

function onConversationSelect(key: string) {
  onConversationChange(key);
  if (effectiveCollapsibleSider.value) {
    siderVisible.value = false;
  }
}
</script>

<style scoped>
.ai-chat-panel {
  display: flex;
  width: 100%;
  min-height: 640px;
  height: 100%;
  border: 1px solid var(--fs-border);
  border-radius: var(--fs-radius-lg);
  overflow: hidden;
  background: var(--fs-bg-surface);
  position: relative;
}

.ai-chat-panel--embedded {
  min-height: calc(100vh - 220px);
}

.ai-chat-panel--compact {
  min-height: 0;
  height: 100%;
  border: none;
  border-radius: 0;
  font-size: 13px;
}

.ai-chat-panel--compact .ai-chat-main {
  padding: 10px 0 8px;
}

.ai-chat-panel--compact .ai-chat-list {
  padding: 0 12px;
}

.ai-chat-panel--compact .ai-chat-sender-wrap {
  padding: 6px 12px 0;
}

.ai-chat-panel--compact .ai-chat-logo-text strong {
  font-size: 13px;
}

.ai-chat-panel--compact .ai-chat-logo-text span {
  font-size: 11px;
}

.ai-chat-panel--compact .ai-chat-toolbar-title {
  font-size: 12px;
}

.ai-chat-panel--compact .ai-chat-new-btn {
  height: 36px;
  font-size: 13px;
}

.ai-chat-panel--compact .ai-chat-clear-all-btn {
  height: 32px;
  font-size: 12px;
}

.ai-chat-panel--compact .ai-chat-bubbles {
  gap: 12px;
  padding: 6px 0 12px;
}

.ai-chat-panel--compact .ai-chat-msg-bubble {
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1.55;
}

.ai-chat-panel--compact .ai-chat-welcome {
  padding: 12px 4px 4px;
}

.ai-chat-panel--compact :deep(.ant-welcome-title) {
  font-size: 16px !important;
}

.ai-chat-panel--compact :deep(.ant-welcome-description) {
  font-size: 12px !important;
  line-height: 1.5 !important;
}

.ai-chat-panel--compact :deep(.ant-prompts-title) {
  font-size: 12px;
}

.ai-chat-panel--compact :deep(.ant-prompts-desc) {
  font-size: 12px;
}

.ai-chat-panel--compact :deep(.ant-prompts-item) {
  font-size: 12px;
}

.ai-chat-panel--compact :deep(.ant-conversations-item) {
  font-size: 13px;
}

.ai-chat-panel--compact :deep(.ant-sender-input) {
  font-size: 13px;
}

.ai-chat-panel--compact :deep(.chat-assistant-step) {
  font-size: 11px;
}

.ai-chat-sider-backdrop {
  position: absolute;
  inset: 0;
  z-index: 4;
  background: rgba(15, 23, 42, 0.28);
}

.ai-chat-sider {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 12px;
  background: color-mix(in srgb, var(--fs-bg-muted) 70%, var(--fs-bg-surface));
  border-right: 1px solid var(--fs-border);
}

.ai-chat-sider--overlay {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 5;
  box-shadow: 8px 0 24px rgba(15, 23, 42, 0.12);
}

.ai-chat-sider-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ai-chat-sider-close {
  flex-shrink: 0;
  color: var(--fs-text-muted);
}

.ai-chat-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px;
  min-width: 0;
}

.ai-chat-logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.ai-chat-logo-text strong {
  color: var(--fs-text-primary);
  font-size: 15px;
}

.ai-chat-logo-text span {
  color: var(--fs-text-muted);
  font-size: 12px;
}

.ai-chat-new-btn {
  height: 40px;
  background: color-mix(in srgb, var(--fs-color-primary) 8%, transparent);
  border-color: color-mix(in srgb, var(--fs-color-primary) 28%, var(--fs-border));
}

.ai-chat-sessions-spin {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.ai-chat-sessions-spin :deep(.ant-spin-container) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.ai-chat-conversations {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0;
  gap: 2px;
}

.ai-chat-conversations :deep(.ant-conversations-list) {
  gap: 2px;
}

.ai-chat-conversations :deep(.ant-conversations-list .ant-conversations-item) {
  padding-inline-start: 8px;
}

.ai-chat-conversations :deep(.ant-conversations-group-title) {
  padding: 0 4px;
  min-height: 32px;
  height: 32px;
}

.ai-chat-conversations :deep(.ant-conversations-item) {
  border: 1px solid transparent;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease;
}

.ai-chat-conversations :deep(.ant-conversations-item:hover:not(.ant-conversations-item-active)) {
  background: color-mix(in srgb, var(--fs-bg-muted) 45%, transparent);
}

.ai-chat-conversations :deep(.ant-conversations-item-active) {
  background: color-mix(in srgb, var(--fs-color-primary) 5%, var(--fs-bg-surface));
  border-color: color-mix(in srgb, var(--fs-color-primary) 24%, var(--fs-border));
}

.ai-chat-clear-all-btn {
  flex-shrink: 0;
  margin-top: 4px;
  height: 36px;
  color: var(--fs-text-muted);
}

.ai-chat-clear-all-btn:not(:disabled):hover {
  color: #ff4d4f;
}

.ai-chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 16px 0 12px;
}

.ai-chat-panel--sider-collapsed .ai-chat-main {
  padding-top: 8px;
}

.ai-chat-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 12px 8px;
  flex-shrink: 0;
}

.ai-chat-toolbar-btn {
  color: var(--fs-text-secondary);
}

.ai-chat-toolbar-title {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--fs-text-primary);
}

.ai-chat-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 16px;
}

.ai-chat-bubbles {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px 0 16px;
}

.ai-chat-msg {
  display: flex;
  width: 100%;
}

.ai-chat-msg--user {
  justify-content: flex-end;
}

.ai-chat-msg--assistant {
  justify-content: flex-start;
}

.ai-chat-msg-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: min(88%, 720px);
  min-width: 0;
  width: 100%;
}

.ai-chat-msg--user .ai-chat-msg-stack {
  width: auto;
}

.ai-chat-msg-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
}

.ai-chat-msg--user .ai-chat-msg-bubble {
  background: color-mix(in srgb, var(--fs-color-primary) 4%, var(--fs-bg-surface));
  border: 1px solid color-mix(in srgb, var(--fs-color-primary) 2%, var(--fs-border));
}

.ai-chat-msg--assistant .ai-chat-msg-bubble {
  background: color-mix(in srgb, var(--fs-bg-muted) 55%, transparent);
  border: 1px solid color-mix(in srgb, var(--fs-border) 90%, transparent);
}

.ai-chat-panel :deep(.ant-bubble .ant-bubble-content-filled) {
  background-color: color-mix(in srgb, var(--fs-bg-muted) 55%, transparent);
}

.ai-chat-welcome {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px 8px 8px;
}

.ai-chat-prompt-grid {
  margin-top: 12px;
}

.ai-chat-prompt-grid :deep(> .ant-prompts > .ant-prompts-list-wrap) {
  flex-direction: column;
  align-items: stretch;
}

.ai-chat-prompt-grid :deep(> .ant-prompts > .ant-prompts-list-wrap > .ant-prompts-item-has-nest) {
  width: 100%;
  flex: none;
}

@media (min-width: 520px) {
  .ai-chat-prompt-grid :deep(> .ant-prompts > .ant-prompts-list-wrap) {
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: stretch;
    gap: 10px;
  }

  .ai-chat-prompt-grid :deep(> .ant-prompts > .ant-prompts-list-wrap > .ant-prompts-item-has-nest) {
    flex: 1 1 0;
    width: auto;
    min-width: 0;
  }
}

.ai-chat-prompt-grid :deep(.ant-prompts-list) {
  gap: 6px;
}

.ai-chat-prompt-grid :deep(.ant-prompts-item) {
  padding-block: 6px;
}

.ai-chat-prompt-grid :deep(.ant-prompts-nested) {
  margin-top: 4px;
}

.ai-chat-prompt-grid :deep(.ant-prompts-item-has-nest > .ant-prompts-content) {
  gap: 2px;
}

.ai-chat-panel :deep(.ant-prompts .ant-prompts-item) {
  background: transparent;
}

.ai-chat-panel :deep(.ant-prompts .ant-prompts-item:not(.ant-prompts-item-has-nest):hover),
.ai-chat-panel :deep(.ant-prompts .ant-prompts-item:not(.ant-prompts-item-has-nest):active) {
  background: transparent;
}

.ai-chat-pending {
  width: 100%;
}

.ai-chat-action-result {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  border: 1px solid transparent;
}

.ai-chat-action-result--executed {
  color: #389e0d;
  background: color-mix(in srgb, #52c41a 10%, var(--fs-bg-surface));
  border-color: color-mix(in srgb, #52c41a 28%, var(--fs-border));
}

.ai-chat-action-result--cancelled {
  color: var(--fs-text-secondary);
  background: color-mix(in srgb, var(--fs-bg-muted) 70%, var(--fs-bg-surface));
  border-color: var(--fs-border);
}

.ai-chat-sender-wrap {
  flex-shrink: 0;
  max-width: 860px;
  width: 100%;
  margin: 0 auto;
  padding: 8px 16px 0;
}

.ai-chat-sender-prompts {
  margin-bottom: 8px;
}

.ai-chat-sender {
  width: 100%;
}
</style>
