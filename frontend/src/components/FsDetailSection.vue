<template>
  <section class="fs-detail-section">
    <h4 v-if="title" class="fs-detail-section__title">{{ title }}</h4>
    <div class="fs-detail-section__body">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
}>();
</script>
