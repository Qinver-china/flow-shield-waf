<template>
  <a-tooltip :title="isDark ? '切换浅色' : '切换深色'">
    <a-button type="text" class="theme-toggle" @click="theme.toggle()">
      <bulb-outlined v-if="isDark" />
      <bg-colors-outlined v-else />
    </a-button>
  </a-tooltip>
</template>

<script setup lang="ts">
import { BgColorsOutlined, BulbOutlined } from "@ant-design/icons-vue";
import { storeToRefs } from "pinia";
import { useThemeStore } from "@/stores/theme";

const theme = useThemeStore();
const { isDark } = storeToRefs(theme);
</script>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--fs-radius-sm);
  color: var(--fs-text-secondary);
  transition: background var(--fs-transition), color var(--fs-transition);
}

.theme-toggle:hover {
  background: var(--fs-bg-muted);
  color: var(--fs-color-primary);
}
</style>
