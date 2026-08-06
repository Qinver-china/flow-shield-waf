<template>
  <div class="app-logo" :class="[`app-logo--${variant}`, { 'app-logo--collapsed': collapsed }]">
    <img
      :src="imageSrc"
      :alt="BRAND.name"
      class="app-logo-image"
      :width="imageSize"
      :height="imageSize"
      decoding="async"
    />
    <span v-if="showText && variant === 'sidebar'" class="app-logo-text">{{ BRAND.name }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import {
  BRAND,
  brandLogoHorizontal,
  brandLogoSquare,
  type BrandSurface,
} from "@/constants/brand";
import { useThemeStore } from "@/stores/theme";

const props = withDefaults(
  defineProps<{
    variant?: "sidebar" | "square" | "horizontal" | "login";
    collapsed?: boolean;
    showText?: boolean;
  }>(),
  {
    variant: "sidebar",
    collapsed: false,
    showText: false,
  },
);

const { isDark } = storeToRefs(useThemeStore());

/** Login left brand panel stays on dark chrome; everything else follows theme. */
const surface = computed<BrandSurface>(() => {
  if (props.variant === "horizontal") return "dark";
  return isDark.value ? "dark" : "light";
});

const useHorizontal = computed(() => {
  if (props.variant === "horizontal" || props.variant === "login") return true;
  // Expanded sidebar / mobile drawer: horizontal wordmark, no companion text.
  if (props.variant === "sidebar" && !props.collapsed) return true;
  return false;
});

const imageSrc = computed(() => {
  // Collapsed sidebar + square/icon slots share the transparent brand mark.
  if (props.variant === "square" || (props.variant === "sidebar" && props.collapsed)) {
    return BRAND.icon;
  }
  if (useHorizontal.value) return brandLogoHorizontal(surface.value);
  return brandLogoSquare(surface.value);
});

const imageSize = computed(() => {
  if (useHorizontal.value) return undefined;
  if (props.variant === "sidebar" && props.collapsed) return 40;
  if (props.variant === "sidebar") return 32;
  return 40;
});
</script>

<style scoped>
.app-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  width: 100%;
}

.app-logo--sidebar {
  padding: 0 4px;
}

.app-logo--sidebar.app-logo--collapsed {
  justify-content: center;
  padding: 0;
  width: auto;
}

.app-logo--horizontal,
.app-logo--login {
  justify-content: flex-start;
}

.app-logo-image {
  display: block;
  flex-shrink: 0;
  object-fit: contain;
}

.app-logo--sidebar.app-logo--collapsed .app-logo-image,
.app-logo--square .app-logo-image {
  border-radius: 0;
}

.app-logo--sidebar:not(.app-logo--collapsed) .app-logo-image,
.app-logo--horizontal .app-logo-image,
.app-logo--login .app-logo-image {
  width: auto;
  max-width: 100%;
  height: auto;
  max-height: 56px;
}

.app-logo--login .app-logo-image {
  max-height: 44px;
}

.app-logo-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--fs-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
