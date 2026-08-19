<template>
  <div class="preset-number-field">
    <div class="preset-number-field__chips">
      <button v-for="opt in presets" :key="String(opt.value)" type="button" class="preset-chip"
        :class="{ 'is-active': !isCustom && modelValue === opt.value }" @click="selectPreset(opt.value)">
        {{ opt.label }}
      </button>
      <button type="button" class="preset-chip" :class="{ 'is-active': isCustom }" @click="selectCustom">
        自定义
      </button>
    </div>
    <div v-if="isCustom || showSlider" class="preset-number-field__controls">

      <a-slider v-if="showSlider && isCustom" class="preset-number-field__slider" :value="modelValue" :min="min"
        :max="max" :step="step" @update:value="onNumberChange" />

      <a-input-number v-if="isCustom" :value="modelValue" :min="min" :max="max" :step="step" :precision="precision"
        class="preset-number-field__input" inputmode="numeric" @update:value="onNumberChange">
        <template v-if="unit" #addonAfter>
          {{ unit }}
        </template>
      </a-input-number>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

export interface PresetOption {
  value: number;
  label: string;
}

const props = withDefaults(
  defineProps<{
    modelValue: number;
    presets: PresetOption[];
    min?: number;
    max?: number;
    step?: number;
    precision?: number;
    unit?: string;
    showSlider?: boolean;
  }>(),
  {
    min: 1,
    max: 9999,
    step: 1,
    precision: 0,
    unit: "",
    showSlider: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: number];
}>();

const presetValues = computed(() => props.presets.map((p) => p.value));

const isCustom = ref(!props.presets.some((p) => p.value === props.modelValue));

watch(
  () => props.modelValue,
  (val) => {
    if (!presetValues.value.includes(val)) {
      isCustom.value = true;
    }
  },
  { immediate: true },
);

function selectPreset(value: number) {
  isCustom.value = false;
  emit("update:modelValue", value);
}

function selectCustom() {
  isCustom.value = true;
}

function onNumberChange(val: number | null) {
  if (val == null || !Number.isFinite(val)) return;
  const clamped = Math.min(props.max, Math.max(props.min, val));
  emit("update:modelValue", clamped);
}
</script>

<style scoped>
.preset-number-field {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.preset-number-field__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preset-chip {
  appearance: none;
  min-height: 36px;
  padding: 6px 14px;
  border: 1px solid var(--fs-border);
  border-radius: var(--fs-radius-sm, 8px);
  background: var(--fs-bg-surface);
  color: var(--fs-text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.preset-chip:hover {
  border-color: color-mix(in srgb, var(--fs-color-primary) 40%, var(--fs-border));
}

.preset-chip.is-active {
  border-color: var(--fs-color-primary);
  background: color-mix(in srgb, var(--fs-color-primary) 10%, var(--fs-bg-surface));
  color: var(--fs-color-primary);
}

.preset-number-field__controls {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.preset-number-field__input {
  flex: 1;
  min-width: 108px;
  max-width: 160px;
}

.preset-number-field__unit {
  font-size: 13px;
  color: var(--fs-text-secondary);
}

.preset-number-field__slider {
  flex: 1 1 100%;
  margin: 2px;
}

@media (max-width: 767px) {
  .preset-number-field__slider :deep(.ant-slider-rail) {
    height: 6px;
  }
}
</style>
