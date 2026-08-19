<template>
  <nav class="settings-nav" aria-label="系统设置分组">
    <div class="settings-nav__mobile">
      <a-segmented
        :value="modelValue"
        :options="mobileOptions"
        block
        class="settings-nav__segmented"
        @change="onSelect"
      />
    </div>
    <ul class="settings-nav__desktop">
      <li v-for="item in items" :key="item.key">
        <button
          type="button"
          class="settings-nav__item"
          :class="{ 'is-active': modelValue === item.key }"
          @click="onSelect(item.key)"
        >
          <component :is="item.icon" class="settings-nav__icon" />
          <span>{{ item.label }}</span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { SettingsGroupKey, SettingsNavItem } from "@/views/settings/settingsGroups";

const props = defineProps<{
  modelValue: SettingsGroupKey;
  items: SettingsNavItem[];
}>();

const emit = defineEmits<{
  "update:modelValue": [key: SettingsGroupKey];
}>();

const mobileOptions = computed(() =>
  props.items.map((item) => ({ value: item.key, label: item.shortLabel })),
);

function onSelect(key: string | number) {
  emit("update:modelValue", String(key) as SettingsGroupKey);
}
</script>

<style scoped>
.settings-nav__mobile {
  display: block;
  margin-bottom: 12px;
}

.settings-nav__desktop {
  display: none;
  list-style: none;
  margin: 0;
  padding: 0;
}

.settings-nav__segmented :deep(.ant-segmented-item-label) {
  padding: 6px;
  font-size: 15px;
}

.settings-nav__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  border: none;
  border-left: 3px solid transparent;
  border-radius: 0 var(--fs-radius-sm) var(--fs-radius-sm) 0;
  background: transparent;
  color: var(--fs-text-secondary);
  font-size: 14px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.settings-nav__item:hover {
  background: color-mix(in srgb, var(--fs-color-primary) 6%, transparent);
  color: var(--fs-text-primary);
}

.settings-nav__item.is-active {
  border-left-color: var(--fs-color-primary);
  background: color-mix(in srgb, var(--fs-color-primary) 10%, transparent);
  color: var(--fs-color-primary);
  font-weight: 600;
}

.settings-nav__icon {
  font-size: 16px;
  flex-shrink: 0;
}

@media (min-width: 992px) {
  .settings-nav__mobile {
    display: none;
  }

  .settings-nav__desktop {
    display: block;
    position: sticky;
    top: 12px;
  }
}
</style>
