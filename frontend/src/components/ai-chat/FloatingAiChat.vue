<template>
  <teleport to="body">
    <transition name="ai-fab-fade">
      <button v-if="showFab" type="button" class="ai-fab" :class="{ 'ai-fab--dragging': isDragging }" :style="fabStyle"
        aria-label="打开 AI 助手（可拖动）" @pointerdown="onFabPointerDown">
        <span class="ai-fab-ring" aria-hidden="true" />
        <span class="ai-fab-glow" aria-hidden="true" />
        <span class="ai-fab-core">
          <svg class="ai-fab-icon" viewBox="0 0 24 24" aria-hidden="true">
            <defs>
              <linearGradient id="aiFabIconGrad" x1="3" y1="2" x2="21" y2="22" gradientUnits="userSpaceOnUse">
                <stop stop-color="#5d3af0" />
                <stop offset="0.48" stop-color="#3a98e3" />
                <stop offset="1" stop-color="#22d3ee" />
              </linearGradient>
            </defs>
            <path fill-rule="evenodd" clip-rule="evenodd" d="M9,4.5C9.334,4.5 9.629,5.723 9.721,6.044L10.534,8.89C10.889,10.135 11.865,11.111 13.11,11.466L15.956,12.279C16.277,12.371 17.499,12.666 17.499,13C17.499,13.334 16.277,13.629 15.956,13.721L13.11,14.534C11.865,14.889 10.889,15.865 10.534,17.11L9.721,19.956C9.629,20.277 9.334,21.499 9,21.499C8.666,21.499 8.371,20.277 8.279,19.956L7.466,17.11C7.111,15.865 6.135,14.889 4.89,14.534L2.044,13.721C1.723,13.629 0.501,13.334 0.501,13C0.501,12.666 1.723,12.371 2.044,12.279L4.89,11.466C6.135,11.111 7.111,10.135 7.466,8.89L8.279,6.044C8.371,5.723 8.666,4.5 9,4.5ZM18,0.5C18.343,0.5 18.645,1.735 18.728,2.068L18.986,3.104C19.222,4.044 19.956,4.778 20.896,5.014L21.932,5.272C22.266,5.355 23.502,5.656 23.502,6C23.502,6.344 22.266,6.645 21.932,6.728L20.896,6.986C19.956,7.222 19.222,7.956 18.986,8.896L18.728,9.932C18.645,10.266 18.344,11.502 18,11.502C17.656,11.502 17.355,10.266 17.272,9.932L17.014,8.896C16.779,7.957 16.043,7.221 15.104,6.986L14.068,6.728C13.734,6.645 12.498,6.344 12.498,6C12.498,5.656 13.734,5.355 14.068,5.272L15.104,5.014C16.043,4.779 16.779,4.043 17.014,3.104L17.272,2.068C17.355,1.735 17.657,0.5 18,0.5ZM18.5,15C18.834,15.006 19.126,16.235 19.212,16.558L19.406,17.155C19.556,17.591 19.9,17.935 20.336,18.085L20.933,18.279C21.254,18.371 22.476,18.666 22.476,19C22.476,19.334 21.254,19.629 20.933,19.721L20.336,19.915C19.9,20.065 19.556,20.409 19.406,20.845L19.212,21.442C19.12,21.763 18.825,22.985 18.491,22.985C18.157,22.985 17.862,21.763 17.77,21.442L17.576,20.845C17.426,20.409 17.082,20.065 16.646,19.915L16.049,19.721C15.728,19.629 14.506,19.334 14.506,19C14.506,18.666 15.728,18.371 16.049,18.279L16.646,18.085C17.082,17.935 17.426,17.591 17.576,17.155L17.77,16.558C17.857,16.228 18.159,14.998 18.5,15Z" style="fill:url(#aiFabIconGrad);"></path>
          </svg>
        </span>
      </button>
    </transition>

    <transition name="ai-panel-slide">
      <div v-show="showFloatPanel" class="ai-float-panel" :class="{ 'ai-float-panel--mobile': isMobile }">
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
          <ai-chat-panel compact collapsible-sider :auto-load-sessions="true" />
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
import { useAiGuardChat } from "@/composables/useAiGuardChat";
import { useBreakpoint } from "@/composables/useBreakpoint";
import { useFabDragPosition } from "@/composables/useFabDragPosition";
import { BRAND } from "@/constants/brand";
import { useFloatingAiChatStore } from "@/stores/floatingAiChat";

const floating = useFloatingAiChatStore();
const { stopGeneration } = useAiGuardChat({ autoLoadSessions: false });
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

watch(
  () => floating.open,
  (open) => {
    if (!open) stopGeneration();
  },
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
  background: linear-gradient(135deg, #2e47ff7d 20%, #d92ea187 35%, #2694cc7d 55%, #54bc0b7d);
  filter: blur(6px);
  opacity: 1;
  animation: ai-fab-spin 3s linear infinite;
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

.ai-fab-icon {
  width: 25px;
  height: 25px;
  display: block;
}

.ai-fab:hover .ai-fab-core {
  transform: scale(1.04);
}

.ai-fab:active .ai-fab-core {
  transform: scale(0.96);
}

@keyframes ai-fab-spin {

  0% {
    transform: rotate(0deg) scale(1);
  }

  50% {
    opacity: 0.6;
    transform: rotate(179deg) scale(.8);
  }

  100% {
    transform: rotate(360deg) scale(1);
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
  background: linear-gradient(90deg,
      color-mix(in srgb, #8b5cf6 6%, var(--fs-bg-surface)) 0%,
      var(--fs-bg-surface) 100%);
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
