<template>
  <div class="fs-json-block">
    <h4 class="fs-json-block__title">{{ title }}</h4>
    <pre class="fs-json-block__content">{{ content }}</pre>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    content: string;
    title?: string;
  }>(),
  { title: "JSON 数据" },
);
</script>
