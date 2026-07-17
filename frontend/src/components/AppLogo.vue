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
import { BRAND } from "@/constants/brand";

const props = withDefaults(
  defineProps<{
    variant?: "sidebar" | "square" | "horizontal" | "login";
    collapsed?: boolean;
    showText?: boolean;
  }>(),
  {
    variant: "sidebar",
    collapsed: false,
    showText: true,
  },
);

const imageSrc = computed(() => {
  if (props.variant === "horizontal" || props.variant === "login") {
    return BRAND.logoHorizontal;
  }
  return BRAND.logoSquare;
});

const imageSize = computed(() => {
  if (props.variant === "horizontal" || props.variant === "login") return undefined;
  if (props.variant === "sidebar" && props.collapsed) return 36;
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
}

.app-logo--sidebar {
  padding: 0 4px;
}

.app-logo--sidebar.app-logo--collapsed {
  justify-content: center;
  padding: 0;
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

.app-logo--sidebar .app-logo-image {
  border-radius: 8px;
}

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
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
