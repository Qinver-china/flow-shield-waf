<template>
  <div class="log-filter-bar">
    <a-card  class="time-bar">
      <div class="time-bar-inner">
        <div class="time-bar-presets">
          <a-radio-group
            :value="filterState.preset.value"
            button-style="solid"
            
            class="preset-group"
            @change="onPresetChange"
          >
            <a-radio-button
              v-for="item in quickTimePresets"
              :key="item.key"
              :value="item.key"
            >
              {{ item.label }}
            </a-radio-button>
            <a-radio-button value="custom">自定义</a-radio-button>
          </a-radio-group>
        </div>

        <div class="time-bar-meta">
          <a-range-picker
            v-if="filterState.preset.value === 'custom'"
            :value="filterState.customRange.value"
            show-time
            
            class="custom-range"
            @change="onCustomRangeChange"
          />
          <span v-else class="time-hint">{{ filterState.rangeLabel() }}</span>
          <a-button
            type="primary"
            class="refresh-btn"
            @click="props.filterState.bumpRefresh()"
          >
            刷新
          </a-button>
        </div>
      </div>
    </a-card>

    <a-card ref="filterCardRef" class="filter-bar-card">
      <a-popover
        v-if="!isCompact"
        v-model:open="filterState.editorOpen.value"
        :trigger="[]"
        placement="bottomLeft"
        overlay-class-name="log-filter-editor-popover"
        :overlay-inner-style="popoverInnerStyle"
        :align="{ offset: [0, 8] }"
        @open-change="onEditorOpenChange"
      >
        <div class="filter-popover-anchor" aria-hidden="true" />
        <template #content>
          <log-filter-editor-content
            :filter-state="filterState"
            :popup-container="editorPopupContainer"
            @apply="applyEditor"
            @cancel="filterState.closeEditor()"
          />
        </template>
      </a-popover>

      <a-drawer
        v-else
        :open="filterState.editorOpen.value"
        placement="bottom"
        height="auto"
        title="筛选条件"
        class="log-filter-editor-drawer"
        :destroy-on-close="false"
        @update:open="onEditorOpenChange"
      >
        <log-filter-editor-content
          :filter-state="filterState"
          @apply="applyEditor"
          @cancel="filterState.closeEditor()"
        />
      </a-drawer>

      <div class="filter-bar-inner">
        <filter-outlined
          class="filter-icon filter-icon-btn"
          role="button"
          tabindex="0"
          aria-label="打开筛选"
          @click="openEditor"
          @keydown.enter.prevent="openEditor"
        />
        <div class="filter-content">
          <template v-if="filterState.hasAppliedFilters.value">
            <a-tag
              v-for="(label, index) in filterState.appliedFilterLabels.value"
              :key="`${label}-${index}`"
              closable
              class="filter-tag filter-tag-clickable"
              @click="openEditor"
              @close.prevent="removeApplied(index)"
            >
              {{ label }}
            </a-tag>
          </template>
          <a-button type="link"  class="add-filter-btn" @click="openEditor">
            + 添加筛选
          </a-button>
          <a-button
            v-if="filterState.hasAppliedFilters.value"
            type="link"
            danger
            class="clear-filter-btn"
            @click="clearFilters"
          >
            清空筛选
          </a-button>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import type { Dayjs } from "dayjs";
import type { Card } from "ant-design-vue";
import { FilterOutlined } from "@ant-design/icons-vue";
import { useBreakpoint } from "@/composables/useBreakpoint";
import LogFilterEditorContent from "./LogFilterEditorContent.vue";
import {
  timePresets,
  type TimePreset,
} from "./constants";
import type { LogFilterState } from "./useLogFilterState";

const props = defineProps<{
  filterState: LogFilterState;
}>();

const filterCardRef = ref<InstanceType<typeof Card> | null>(null);
const popoverCardWidth = ref<number>();

let cardResizeObserver: ResizeObserver | null = null;

const popoverInnerStyle = computed(() => {
  if (!popoverCardWidth.value) return undefined;
  return { width: `${popoverCardWidth.value}px` };
});

function syncPopoverCardWidth() {
  const cardEl = filterCardRef.value?.$el as HTMLElement | undefined;
  popoverCardWidth.value = cardEl?.getBoundingClientRect().width;
}

onMounted(() => {
  syncPopoverCardWidth();
  const cardEl = filterCardRef.value?.$el as HTMLElement | undefined;
  if (!cardEl || typeof ResizeObserver === "undefined") return;
  cardResizeObserver = new ResizeObserver(() => syncPopoverCardWidth());
  cardResizeObserver.observe(cardEl);
});

onUnmounted(() => {
  cardResizeObserver?.disconnect();
  cardResizeObserver = null;
});

const { isMobile, isTablet } = useBreakpoint();
const isCompact = computed(() => isMobile.value || isTablet.value);

const quickTimePresets = timePresets.filter((item) => item.key !== "custom");

const presetOptions = computed(() => [
  ...quickTimePresets.map((item) => ({ value: item.key, label: item.label })),
  { value: "custom", label: "自定义" },
]);

function onPresetChange(event: { target: { value: TimePreset } }) {
  props.filterState.setPreset(event.target.value);
}

function onPresetSelectChange(value: TimePreset) {
  props.filterState.setPreset(value);
}

function onCustomRangeChange(value: [Dayjs, Dayjs] | null) {
  if (!value || value.length !== 2) return;
  props.filterState.setCustomRange(value);
}

function openEditor() {
  if (props.filterState.editorOpen.value) return;
  props.filterState.openEditor(
    props.filterState.appliedConditions.value.length
      ? props.filterState.appliedConditions.value
      : undefined,
  );
}

function onEditorOpenChange(open: boolean) {
  if (!open) props.filterState.closeEditor();
}

function editorPopupContainer(triggerNode: HTMLElement) {
  const editor = document.querySelector(".log-filter-editor-popover");
  return (editor as HTMLElement) || triggerNode.parentElement || document.body;
}

function applyEditor() {
  props.filterState.applyDraft();
}

function clearFilters() {
  props.filterState.clearAppliedFilters();
}

function removeApplied(index: number) {
  props.filterState.removeAppliedCondition(index);
}
</script>

<style scoped>
.log-filter-bar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.time-bar :deep(.ant-card-body) {
  padding: 10px 12px;
}

.time-bar-inner {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.time-bar-presets {
  min-width: 0;
}

.preset-select {
  width: 100%;
}

.preset-group {
  display: block;
  width: 100%;
}

.preset-group :deep(.ant-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  width: 100%;
}

.preset-group :deep(.ant-radio-button-wrapper) {
  flex: 0 1 auto;
  margin: 2px;
  height: 28px;
  line-height: 26px;
  padding-inline: 10px;
  font-size: 12px;
  border-radius: 6px !important;
  border-inline-start-width: 1px;
}

.preset-group :deep(.ant-radio-button-wrapper:not(:first-child)::before) {
  display: none;
}

.log-filter-editor-popover .ant-popover-inner{
  max-width: 700px;
}

.time-bar-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.custom-range {
  flex: 1 1 240px;
  min-width: 0;
  max-width: 100%;
}

.time-hint {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  word-break: break-all;
}

.refresh-btn {
  margin-left: auto;
  flex-shrink: 0;
}

@media (min-width: 1024px) {
  .time-bar-inner {
    flex-direction: row;
    align-items: center;
    gap: 12px;
  }

  .time-bar-presets {
    flex: 1 1 auto;
    min-width: 0;
  }

  .time-bar-meta {
    flex: 0 0 auto;
    max-width: 46%;
  }

  .custom-range {
    flex: 1 1 280px;
    max-width: 360px;
  }
}

@media (max-width: 1023px) {
  .time-bar-meta {
    width: 100%;
  }

  .refresh-btn {
    margin-left: 0;
  }

  .custom-range :deep(.ant-picker) {
    width: 100%;
  }
}

.filter-bar-card :deep(.ant-card-body) {
  position: relative;
  padding: 10px 14px;
}

.filter-popover-anchor {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 0;
  pointer-events: none;
}

.filter-bar-inner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.filter-icon {
  margin-top: 7px;
  color: var(--fs-text-muted);
  font-size: 18px;
}

.filter-icon-btn {
  flex-shrink: 0;
  cursor: pointer;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}

.filter-icon-btn:hover,
.filter-icon-btn:focus-visible {
  color: var(--fs-color-primary);
  background: color-mix(in srgb, var(--fs-color-primary) 8%, transparent);
  outline: none;
}

.filter-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.filter-tag {
  margin: 0;
  max-width: 100%;
  padding: 3px 6px;
}

.filter-tag-clickable {
  cursor: pointer;
}

.filter-tag-clickable:hover {
  border-color: color-mix(in srgb, var(--fs-color-primary) 35%, var(--fs-border));
  color: var(--fs-color-primary);
}

.add-filter-btn,
.clear-filter-btn {
  padding-inline: 0;
}
</style>

<style>
.log-filter-editor-drawer .ant-drawer-content-wrapper {
  max-height: 85vh;
}

.log-filter-editor-drawer .ant-drawer-body {
  max-height: calc(85vh - 56px);
  overflow-y: auto;
  padding-top: 8px;
}
</style>
