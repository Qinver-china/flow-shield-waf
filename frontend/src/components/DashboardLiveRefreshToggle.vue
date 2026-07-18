<template>
  <a-tooltip title="开启后总览数据每 8 秒自动刷新">
    <label class="live-refresh-toggle">
      <span class="live-refresh-label">自动刷新</span>
      <a-switch :checked="enabled" size="small" @change="onChange" />
    </label>
  </a-tooltip>
</template>

<script setup lang="ts">
import { SyncOutlined } from "@ant-design/icons-vue";
import { useDashboardLiveRefresh } from "@/composables/useDashboardLiveRefresh";

const { enabled, setEnabled } = useDashboardLiveRefresh();

function onChange(checked: boolean) {
  setEnabled(checked);
}
</script>

<style scoped>
.live-refresh-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  padding: 4px 8px;
  border-radius: var(--fs-radius-sm);
  cursor: pointer;
  color: var(--fs-text-secondary);
  transition: background var(--fs-transition);
}

.live-refresh-toggle:hover {
  background: var(--fs-bg-muted);
}

.live-refresh-label {
  font-size: 13px;
  user-select: none;
}

.spinning {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 767px) {
  .live-refresh-label {
    display: none;
  }
}
</style>
