import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";

export type ThemeMode = "light" | "dark";

const STORAGE_KEY = "waf_theme_mode";

function readStored(): ThemeMode {
  const v = localStorage.getItem(STORAGE_KEY);
  return v === "dark" ? "dark" : "light";
}

export const useThemeStore = defineStore("theme", () => {
  const mode = ref<ThemeMode>(readStored());

  const isDark = computed(() => mode.value === "dark");

  function applyDom() {
    document.documentElement.setAttribute("data-theme", mode.value);
  }

  function setMode(next: ThemeMode) {
    mode.value = next;
    localStorage.setItem(STORAGE_KEY, next);
    applyDom();
  }

  function toggle() {
    setMode(mode.value === "dark" ? "light" : "dark");
  }

  watch(mode, applyDom, { immediate: true });

  return { mode, isDark, setMode, toggle };
});
