import { defineStore } from "pinia";
import { ref } from "vue";

export const useFloatingAiChatStore = defineStore("floatingAiChat", () => {
  const open = ref(false);
  const lastSessionId = ref<number | null>(null);

  function toggle() {
    open.value = !open.value;
  }

  function show() {
    open.value = true;
  }

  function hide() {
    open.value = false;
  }

  function setLastSessionId(id: number | null) {
    lastSessionId.value = id;
  }

  return { open, lastSessionId, toggle, show, hide, setLastSessionId };
});
