import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "@/api";

/** 仅在 AI 总开关与悬浮助手均开启时显示悬浮球 */
function resolveFabVisible(settings: {
  enabled?: boolean;
  floating_chat_enabled?: boolean;
}): boolean {
  return Boolean(settings.enabled) && settings.floating_chat_enabled !== false;
}

export const useFloatingAiChatStore = defineStore("floatingAiChat", () => {
  const open = ref(false);
  const lastSessionId = ref<number | null>(null);
  /** 是否显示右下角悬浮 AI 按钮；默认隐藏，启动后从 AI 配置同步 */
  const fabEnabled = ref(false);
  const fabPreferenceLoaded = ref(false);

  function toggle() {
    open.value = !open.value;
  }

  function show() {
    if (!fabEnabled.value) return;
    open.value = true;
  }

  function hide() {
    open.value = false;
  }

  function setLastSessionId(id: number | null) {
    lastSessionId.value = id;
  }

  function setFabEnabled(enabled: boolean) {
    fabEnabled.value = enabled;
    if (!enabled) {
      open.value = false;
    }
  }

  async function fetchFabPreference() {
    try {
      const res = await api.get<{
        enabled?: boolean;
        floating_chat_enabled?: boolean;
      }>("/api/v1/ai-guard/settings");
      setFabEnabled(resolveFabVisible(res.data));
    } catch {
      // 接口异常时保持隐藏，避免未启用 AI 时误显示悬浮球
      setFabEnabled(false);
    } finally {
      fabPreferenceLoaded.value = true;
    }
  }

  return {
    open,
    lastSessionId,
    fabEnabled,
    fabPreferenceLoaded,
    toggle,
    show,
    hide,
    setLastSessionId,
    setFabEnabled,
    fetchFabPreference,
  };
});
