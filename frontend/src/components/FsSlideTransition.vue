<template>
  <div class="fs-slide-stage">
    <transition name="fs-slide" mode="out-in">
      <div :key="String(transitionKey)" class="fs-slide-panel">
        <slot />
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  transitionKey: string | number;
}>();
</script>
