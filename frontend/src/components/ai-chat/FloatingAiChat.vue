<template>
  <teleport to="body">
    <transition name="ai-fab-fade">
      <button
        v-if="showFab"
        type="button"
        class="ai-fab"
        :class="{ 'ai-fab--dragging': isDragging }"
        :style="fabStyle"
        aria-label="打开 AI 助手（可拖动）"
        @pointerdown="onFabPointerDown"
      >
        <span class="ai-fab-ring" aria-hidden="true" />
        <span class="ai-fab-glow" aria-hidden="true" />
        <span class="ai-fab-core">
          <img :src="BRAND.icon" :alt="BRAND.name" class="ai-fab-logo" />
        </span>
      </button>
    </transition>

    <transition name="ai-panel-slide">
      <div
        v-show="showFloatPanel"
        class="ai-float-panel"
        :class="{ 'ai-float-panel--mobile': isMobile }"
      >
        <div class="ai-float-header">
          <div class="ai-float-title">
            <span class="ai-float-title-icon">
              <img :src="BRAND.icon" :alt="BRAND.name" />
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
import { computed, onMounted, watch } from "vue";
import { CloseOutlined } from "@ant-design/icons-vue";
import { useRoute, useRouter } from "vue-router";
import AiChatPanel from "@/components/ai-chat/AiChatPanel.vue";
import { useBreakpoint } from "@/composables/useBreakpoint";
import { useFabDragPosition } from "@/composables/useFabDragPosition";
import { BRAND } from "@/constants/brand";
import { useFloatingAiChatStore } from "@/stores/floatingAiChat";

const floating = useFloatingAiChatStore();
const route = useRoute();
const router = useRouter();
const { isMobile } = useBreakpoint();

const isOnAiGuardPage = computed(
  () => route.path === "/ai-guard" || route.path.startsWith("/ai-guard/"),
);
const showFab = computed(
  () => floating.fabEnabled && !floating.open && !isOnAiGuardPage.value,
);
const showFloatPanel = computed(
  () => floating.fabEnabled && floating.open && !isOnAiGuardPage.value,
);

watch(isOnAiGuardPage, (onPage) => {
  if (onPage && floating.open) {
    floating.hide();
  }
});

onMounted(() => {
  if (!floating.fabPreferenceLoaded) {
    void floating.fetchFabPreference();
  }
});

const { fabPos, isDragging, onFabPointerDown } = useFabDragPosition({
  onTap: () => floating.show(),
});

const fabStyle = computed(() => ({
  left: `${fabPos.value.x}px`,
  top: `${fabPos.value.y}px`,
}));

function goFullPage() {
  floating.hide();
  void router.push("/ai-guard");
}
</script>

<style scoped>
.ai-fab {
  position: fixed;
  z-index: 1100;
  width: 48px;
  height: 48px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: grab;
  outline: none;
  touch-action: none;
  user-select: none;
}

.ai-fab--dragging {
  cursor: grabbing;
}

.ai-fab--dragging .ai-fab-core {
  transform: scale(1.02);
}

.ai-fab-ring {
  display: none;
}

.ai-fab-glow {
  position: absolute;
  top: -6px;
  right: -6px;
  bottom: -6px;
  left: -6px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f196, #8b5cf6c7 45%, #22d3eed1);
  filter: blur(6px);
  opacity: 1;
  animation: ai-fab-pulse-ea48bc1f 2.8s ease-in-out infinite, ai-fab-spin-ea48bc1f 3s linear infinite;
}

.ai-fab-core {
  position: absolute;
  top: 3px;
  right: 3px;
  bottom: 3px;
  left: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: color-mix(in srgb, var(--fs-bg-elevated) 90%, transparent);
}

.ai-fab-logo {
  width: 26px;
  height: 26px;
  object-fit: contain;
  transition: .2s;
}

.ai-fab:hover .ai-fab-core {
  transform: scale(1.04);
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
  width: min(600px, calc(100vw - 40px));
  height: min(720px, calc(100vh - 40px));
  display: flex;
  flex-direction: column;
  border-radius: var(--fs-radius-lg);
  overflow: hidden;
  background: var(--fs-bg-modal);
  border: 1px solid var(--fs-border);
  box-shadow: 0px 0px 12px 5px #5353531c;
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
}

.ai-float-title-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
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
