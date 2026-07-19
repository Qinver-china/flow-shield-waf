import { defineStore } from "pinia";
import { ref } from "vue";

export const useFloatingAiChatStore = defineStore("floatingAiChat", () => {
  const open = ref(false);
  const panelKey = ref(0);

  function toggle() {
    open.value = !open.value;
    if (open.value) {
      panelKey.value += 1;
    }
  }

  function show() {
    open.value = true;
    panelKey.value += 1;
  }

  function hide() {
    open.value = false;
  }

  return { open, panelKey, toggle, show, hide };
});
