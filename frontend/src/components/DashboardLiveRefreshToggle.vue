<template>
  <label class="live-refresh-switch">
    <span class="live-refresh-switch__label">自动刷新</span>
    <a-switch
      size="small"
      :checked="enabled"
      :aria-label="tooltip"
      @change="(checked: boolean) => setEnabled(checked)"
    />
  </label>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useDashboardLiveRefresh } from "@/composables/useDashboardLiveRefresh";

const { enabled, setEnabled } = useDashboardLiveRefresh();

const tooltip = computed(() =>
  enabled.value ? "关闭自动刷新（每 8 秒）" : "开启自动刷新（每 8 秒）",
);
</script>

<style scoped>
.live-refresh-switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.live-refresh-switch__label {
  font-size: 13px;
  color: var(--fs-text-secondary);
  line-height: 1;
}
</style>
