<template>
  <span>{{ formatSiteIds(siteIds) }}</span>
</template>

<script setup lang="ts">
import { useSiteOptions } from "@/composables/useSiteOptions";

defineProps<{ siteIds?: number[] | null }>();

const { formatSiteIds } = useSiteOptions();
</script>
