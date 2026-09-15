<template>
  <a-tooltip :title="tooltip">
    <a-button
      type="text"
      class="fs-header-icon-btn theme-toggle"
      :aria-label="tooltip"
      @click="theme.toggle()"
    >
      <MorphIcon
        :icon="isDark ? Sun : Moon"
        :size="17"
        spring="snappy"
        color="currentColor"
        :class="[
          'theme-toggle__icon',
          isDark ? 'theme-toggle__icon--day' : 'theme-toggle__icon--night',
        ]"
      />
    </a-button>
  </a-tooltip>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { MorphIcon } from "morphicons/vue";
import { Moon, Sun } from "lucide";
import { useThemeStore } from "@/stores/theme";

const theme = useThemeStore();
const { isDark } = storeToRefs(theme);

const tooltip = computed(() => (isDark.value ? "切换日间模式" : "切换夜间模式"));
</script>

<style scoped>
.theme-toggle__icon {
  display: block;
  transition: color var(--fs-transition);
}

.fs-header-icon-btn:hover .theme-toggle__icon--day {
  color: #f59e0b;
}

.fs-header-icon-btn:hover .theme-toggle__icon--night {
  color: var(--fs-color-primary);
}
</style>
