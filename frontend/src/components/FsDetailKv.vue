<template>
  <div class="fs-detail-kv">
    <div v-for="item in items" :key="item.label" class="fs-detail-kv__row">
      <div class="fs-detail-kv__label">{{ item.label }}</div>
      <div class="fs-detail-kv__value">
        <a-tag v-if="item.tag" :color="item.tagColor">{{ item.value ?? "-" }}</a-tag>
        <span v-else>{{ item.value ?? "-" }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface DetailKvItem {
  label: string;
  value?: string | number | null;
  tag?: boolean;
  tagColor?: string;
}

defineProps<{
  items: DetailKvItem[];
}>();
</script>
