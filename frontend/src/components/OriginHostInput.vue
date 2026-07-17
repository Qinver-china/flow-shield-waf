<template>
  <a-auto-complete
    v-model:value="value"
    :options="presets"
    :disabled="disabled"
    :placeholder="placeholder"
    :open="dropdownOpen"
    :filter-option="filterOption"
    allow-clear
    style="width: 100%"
    @dropdown-visible-change="onDropdownChange"
    @focus="onFocus"
  >
    <template #option="{ value: optValue, description }">
      <div class="origin-option">
        <span class="origin-option-value">{{ optValue }}</span>
        <span v-if="description" class="origin-option-desc">{{ description }}</span>
      </div>
    </template>
  </a-auto-complete>
</template>

<script setup lang="ts">
import { ref } from "vue";

const value = defineModel<string>("value", { default: "" });

const props = withDefaults(
  defineProps<{
    disabled?: boolean;
    placeholder?: string;
  }>(),
  {
    disabled: false,
    placeholder: "127.0.0.1 或 host.docker.internal",
  },
);

const presets = [
  { value: "127.0.0.1", description: "本机回环地址" },
  { value: "localhost", description: "本机主机名" },
  { value: "host.docker.internal", description: "Docker 容器访问宿主机" },
  { value: "172.17.0.1", description: "Docker 默认网桥网关（Linux）" },
];

const dropdownOpen = ref(false);

function filterOption(input: string, option: { value: string; description?: string }) {
  const q = input.toLowerCase();
  return (
    option.value.toLowerCase().includes(q) ||
    Boolean(option.description?.toLowerCase().includes(q))
  );
}

function onFocus() {
  if (!props.disabled) dropdownOpen.value = true;
}

function onDropdownChange(open: boolean) {
  dropdownOpen.value = open;
}
</script>

<style scoped>
.origin-option {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.origin-option-value {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  color: #0f172a;
}

.origin-option-desc {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}
</style>
