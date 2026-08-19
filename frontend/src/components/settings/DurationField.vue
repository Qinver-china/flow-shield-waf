<template>
  <div class="duration-field">
    <div v-if="quickPresets.length" class="duration-field__chips">
      <button
        v-for="preset in quickPresets"
        :key="preset.seconds"
        type="button"
        class="preset-chip"
        :class="{ 'is-active': modelValue === preset.seconds }"
        @click="emit('update:modelValue', preset.seconds)"
      >
        {{ preset.label }}
      </button>
    </div>
    <div class="duration-field__row">
      <a-input-number
        :value="displayAmount"
        :min="minAmount"
        :max="maxAmount"
        :step="1"
        :precision="0"
        class="duration-field__input"
        inputmode="numeric"
        @update:value="onAmountChange"
      />
      <a-segmented
        v-model:value="unit"
        :options="unitOptions"
        class="duration-field__units"
        @change="onUnitChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

export interface DurationPreset {
  seconds: number;
  label: string;
}

const props = withDefaults(
  defineProps<{
    modelValue: number;
    minSeconds?: number;
    maxSeconds?: number;
    quickPresets?: DurationPreset[];
    units?: Array<"second" | "minute" | "hour" | "day">;
  }>(),
  {
    minSeconds: 60,
    maxSeconds: 604800,
    quickPresets: () => [],
    units: () => ["minute", "hour", "day"],
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: number];
}>();

const UNIT_SECONDS: Record<string, number> = {
  second: 1,
  minute: 60,
  hour: 3600,
  day: 86400,
};

const UNIT_LABELS: Record<string, string> = {
  second: "秒",
  minute: "分钟",
  hour: "小时",
  day: "天",
};

const unitOptions = computed(() =>
  props.units.map((u) => ({ value: u, label: UNIT_LABELS[u] || u })),
);

function pickUnit(seconds: number): string {
  if (props.units.includes("day") && seconds % 86400 === 0) return "day";
  if (props.units.includes("hour") && seconds % 3600 === 0) return "hour";
  if (props.units.includes("minute") && seconds % 60 === 0) return "minute";
  if (props.units.includes("second")) return "second";
  return props.units[0] || "minute";
}

const unit = ref(pickUnit(props.modelValue));

watch(
  () => props.modelValue,
  (val) => {
    unit.value = pickUnit(val);
  },
);

const displayAmount = computed(() => {
  const factor = UNIT_SECONDS[unit.value] || 60;
  return Math.round(props.modelValue / factor);
});

const minAmount = computed(() => Math.ceil(props.minSeconds / (UNIT_SECONDS[unit.value] || 1)));
const maxAmount = computed(() => Math.floor(props.maxSeconds / (UNIT_SECONDS[unit.value] || 1)));

function clampSeconds(seconds: number) {
  return Math.min(props.maxSeconds, Math.max(props.minSeconds, Math.round(seconds)));
}

function onAmountChange(val: number | null) {
  if (val == null || !Number.isFinite(val)) return;
  const factor = UNIT_SECONDS[unit.value] || 1;
  emit("update:modelValue", clampSeconds(val * factor));
}

function onUnitChange(next: string | number) {
  const nextUnit = String(next);
  const currentSeconds = props.modelValue;
  const factor = UNIT_SECONDS[nextUnit] || 1;
  const amount = Math.max(1, Math.round(currentSeconds / factor));
  emit("update:modelValue", clampSeconds(amount * factor));
}
</script>

<style scoped>
.duration-field {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.duration-field__chips {
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

.preset-chip.is-active {
  border-color: var(--fs-color-primary);
  background: color-mix(in srgb, var(--fs-color-primary) 10%, var(--fs-bg-surface));
  color: var(--fs-color-primary);
}

.duration-field__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.duration-field__input {
  min-width: 80px;
  max-width: 100px;
}

.duration-field__units {
  flex-shrink: 0;
}


</style>
