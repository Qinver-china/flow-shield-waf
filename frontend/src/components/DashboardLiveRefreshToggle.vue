<template>
  <a-tooltip :title="tooltip">
    <a-button
      type="text"
      class="fs-header-icon-btn"
      :class="{ 'fs-header-icon-btn--active': enabled }"
      :aria-label="tooltip"
      @click="setEnabled(!enabled)"
    >
      <sync-outlined :class="{ 'fs-icon-spin': enabled }" />
    </a-button>
  </a-tooltip>
</template>

<script setup lang="ts">
import { SyncOutlined } from "@ant-design/icons-vue";
import { computed } from "vue";
import { useDashboardLiveRefresh } from "@/composables/useDashboardLiveRefresh";

const { enabled, setEnabled } = useDashboardLiveRefresh();

const tooltip = computed(() =>
  enabled.value ? "关闭自动刷新（每 8 秒）" : "开启自动刷新（每 8 秒）",
);
</script>
