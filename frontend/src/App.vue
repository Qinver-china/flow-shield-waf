<template>
  <a-config-provider :locale="zhCN" :theme="antdTheme">
    <div class="fs-app-root">
      <div class="fs-app-bg" aria-hidden="true" />
      <div class="fs-app-shell">
        <router-view />
      </div>
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import zhCN from "ant-design-vue/es/locale/zh_CN";
import { useThemeStore } from "@/stores/theme";
import { buildAntdTheme } from "@/utils/antdTheme";

const themeStore = useThemeStore();
const { isDark } = storeToRefs(themeStore);

const antdTheme = computed(() => buildAntdTheme(isDark.value));
</script>

<style scoped>
.fs-app-root {
  position: relative;
  min-height: 100%;
}

.fs-app-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: var(--fs-bg-body);
}

.fs-app-shell {
  position: relative;
  z-index: 1;
  min-height: 100%;
}
</style>
