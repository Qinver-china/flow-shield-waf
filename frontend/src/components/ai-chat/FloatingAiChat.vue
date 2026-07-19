<template>
  <teleport to="body">
    <transition name="ai-fab-fade">
      <button
        v-if="!floating.open"
        type="button"
        class="ai-fab"
        aria-label="打开 AI 助手"
        @click="openPanel"
      >
        <span class="ai-fab-ring" aria-hidden="true" />
        <span class="ai-fab-glow" aria-hidden="true" />
        <span class="ai-fab-core">
          <img :src="BRAND.logoSquare" :alt="BRAND.name" class="ai-fab-logo" />
        </span>
      </button>
    </transition>

    <transition name="ai-panel-slide">
      <div v-if="floating.open" class="ai-float-panel" :class="{ 'ai-float-panel--mobile': isMobile }">
        <div class="ai-float-header">
          <div class="ai-float-title">
            <span class="ai-float-title-icon">
              <img :src="BRAND.logoSquare" :alt="BRAND.name" />
            </span>
            <span>AI 智能助手</span>
          </div>
          <a-space>
            <a-button type="link" size="small" @click="goFullPage">完整页面</a-button>
            <a-button type="text" size="small" @click="floating.hide()">
              <close-outlined />
            </a-button>
          </a-space>
        </div>
        <div class="ai-float-body">
          <ai-chat-panel
            :key="floating.panelKey"
            compact
            collapsible-sider
            :auto-load-sessions="true"
          />
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import { CloseOutlined } from "@ant-design/icons-vue";
import { useRouter } from "vue-router";
import AiChatPanel from "@/components/ai-chat/AiChatPanel.vue";
import { useBreakpoint } from "@/composables/useBreakpoint";
import { BRAND } from "@/constants/brand";
import { useFloatingAiChatStore } from "@/stores/floatingAiChat";

const floating = useFloatingAiChatStore();
const router = useRouter();
const { isMobile } = useBreakpoint();

function openPanel() {
  floating.show();
}

function goFullPage() {
  floating.hide();
  void router.push("/ai-guard");
}
</script>

<style scoped>
.ai-fab {
  position: fixed;
  right: 22px;
  bottom: 22px;
  z-index: 1100;
  width: 48px;
  height: 48px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  outline: none;
}

.ai-fab-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: linear-gradient(
    135deg,
    #6366f1 0%,
    #8b5cf6 45%,
    #22d3ee 100%
  );
  animation: ai-fab-spin 8s linear infinite;
}

.ai-fab-glow {
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    color-mix(in srgb, #8b5cf6 35%, transparent) 0%,
    transparent 70%
  );
  filter: blur(6px);
  opacity: 0.85;
  animation: ai-fab-pulse 2.8s ease-in-out infinite;
}

.ai-fab-core {
  position: absolute;
  inset: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(
    160deg,
    color-mix(in srgb, #ffffff 92%, #eef2ff) 0%,
    color-mix(in srgb, #f5f3ff 88%, #e0e7ff) 100%
  );
  box-shadow:
    0 6px 20px color-mix(in srgb, #6366f1 28%, transparent),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.ai-fab-logo {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  object-fit: cover;
}

.ai-fab:hover .ai-fab-core {
  transform: scale(1.04);
  box-shadow:
    0 8px 24px color-mix(in srgb, #6366f1 36%, transparent),
    inset 0 1px 0 rgba(255, 255, 255, 0.95);
}

.ai-fab:active .ai-fab-core {
  transform: scale(0.96);
}

@keyframes ai-fab-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes ai-fab-pulse {
  0%,
  100% {
    opacity: 0.65;
    transform: scale(0.98);
  }
  50% {
    opacity: 1;
    transform: scale(1.04);
  }
}

.ai-float-panel {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 1100;
  width: min(720px, calc(100vw - 40px));
  height: min(720px, calc(100vh - 40px));
  display: flex;
  flex-direction: column;
  border-radius: var(--fs-radius-lg);
  overflow: hidden;
  background: var(--fs-bg-surface);
  border: 1px solid color-mix(in srgb, #8b5cf6 18%, var(--fs-border));
  box-shadow:
    0 16px 48px rgba(15, 23, 42, 0.18),
    0 0 0 1px color-mix(in srgb, #8b5cf6 8%, transparent);
}

.ai-float-panel--mobile {
  right: 0;
  bottom: 0;
  width: 100vw;
  height: 100vh;
  border-radius: 0;
}

.ai-float-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px 10px 16px;
  border-bottom: 1px solid var(--fs-border);
  background: linear-gradient(
    90deg,
    color-mix(in srgb, #8b5cf6 6%, var(--fs-bg-surface)) 0%,
    var(--fs-bg-surface) 100%
  );
}

.ai-float-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--fs-text-primary);
}

.ai-float-title-icon {
  display: inline-flex;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px color-mix(in srgb, #6366f1 20%, transparent);
}

.ai-float-title-icon img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ai-float-body {
  flex: 1;
  min-height: 0;
}

.ai-fab-fade-enter-active,
.ai-fab-fade-leave-active,
.ai-panel-slide-enter-active,
.ai-panel-slide-leave-active {
  transition: all 0.22s ease;
}

.ai-fab-fade-enter-from,
.ai-fab-fade-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

.ai-panel-slide-enter-from,
.ai-panel-slide-leave-to {
  opacity: 0;
  transform: translateY(16px) scale(0.98);
}
</style>
