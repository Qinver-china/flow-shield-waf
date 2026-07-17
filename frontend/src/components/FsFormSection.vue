<template>
  <section class="fs-form-section">
    <div v-if="title || description || $slots.extra" class="fs-form-section__head">
      <div v-if="title || $slots.extra" class="fs-form-section__title-row">
        <h4 v-if="title" class="fs-form-section__title">{{ title }}</h4>
        <div v-if="$slots.extra" class="fs-form-section__extra">
          <slot name="extra" />
        </div>
      </div>
      <p v-if="description" class="fs-form-section__desc">{{ description }}</p>
    </div>
    <div class="fs-form-section__body">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
  description?: string;
}>();
</script>
