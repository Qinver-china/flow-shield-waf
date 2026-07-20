import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "@/api";

export const useFloatingAiChatStore = defineStore("floatingAiChat", () => {
  const open = ref(false);
  const lastSessionId = ref<number | null>(null);
  /** 是否显示右下角悬浮 AI 按钮；默认开启，启动后从 AI 配置同步 */
  const fabEnabled = ref(true);
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
      const res = await api.get<{ floating_chat_enabled?: boolean }>("/api/v1/ai-guard/settings");
      setFabEnabled(res.data.floating_chat_enabled !== false);
    } catch {
      // 保持默认开启，避免设置接口异常时误藏按钮
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
