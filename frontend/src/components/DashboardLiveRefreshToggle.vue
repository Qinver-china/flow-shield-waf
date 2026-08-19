<template>
  <a-tooltip :title="tooltip" placement="bottomRight">
    <button
      type="button"
      class="live-refresh-ctrl"
      :class="{ 'is-live': enabled }"
      :aria-label="tooltip"
      @click="toggle"
    >
      <span class="live-refresh-ctrl__time">{{ lastUpdated }}</span>
      <span class="live-refresh-ctrl__state" aria-hidden="true">
        <span v-if="enabled" class="live-refresh-ctrl__dot" />
        <pause-outlined v-else class="live-refresh-ctrl__pause" />
      </span>
    </button>
  </a-tooltip>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { PauseOutlined } from "@ant-design/icons-vue";
import { useDashboardLiveRefresh } from "@/composables/useDashboardLiveRefresh";

const props = defineProps<{
  lastUpdated?: string;
}>();

const { enabled, setEnabled } = useDashboardLiveRefresh();

const tooltip = computed(() => {
  const time = props.lastUpdated ? `更新于 ${props.lastUpdated}` : "";
  if (enabled.value) {
    return time ? `${time} · 自动刷新中` : "自动刷新中";
  }
  return time ? `${time} · 已暂停，点击恢复` : "已暂停，点击恢复";
});

function toggle() {
  setEnabled(!enabled.value);
}
</script>

<style scoped>
.live-refresh-ctrl {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 10px;
  border: 1px solid var(--fs-border);
  border-radius: 999px;
  background: var(--fs-bg-elevated, var(--fs-bg-surface));
  color: var(--fs-text-secondary);
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  user-select: none;
  transition:
    border-color var(--fs-transition),
    background var(--fs-transition),
    color var(--fs-transition);
}

.live-refresh-ctrl:hover {
  border-color: color-mix(in srgb, var(--fs-color-primary) 35%, var(--fs-border));
  color: var(--fs-text-primary);
}

.live-refresh-ctrl:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--fs-color-primary) 45%, transparent);
  outline-offset: 2px;
}

.live-refresh-ctrl.is-live {
  border-color: color-mix(in srgb, var(--fs-color-accent) 30%, var(--fs-border));
  background: color-mix(in srgb, var(--fs-color-accent) 8%, var(--fs-bg-elevated, var(--fs-bg-surface)));
}

.live-refresh-ctrl.is-live:hover {
  border-color: color-mix(in srgb, var(--fs-color-accent) 45%, var(--fs-border));
}

.live-refresh-ctrl__time {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.01em;
}

.live-refresh-ctrl__state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.live-refresh-ctrl__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--fs-color-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--fs-color-accent) 24%, transparent);
  animation: live-refresh-pulse 1.6s ease-out infinite;
}

.live-refresh-ctrl__pause {
  font-size: 12px;
  color: var(--fs-text-muted);
}

@keyframes live-refresh-pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--fs-color-accent) 40%, transparent);
  }

  70% {
    box-shadow: 0 0 0 6px transparent;
  }

  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}
</style>
