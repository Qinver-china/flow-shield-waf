<template>
  <div class="percent-slider-field">
    <a-slider
      class="percent-slider-field__slider"
      :value="modelValue"
      :min="0"
      :max="100"
      :step="1"
      @update:value="onInput"
    />
    <a-input-number
      :value="modelValue"
      :min="0"
      :max="100"
      :step="1"
      :precision="0"
      addon-after="%"
      class="percent-slider-field__input"
      inputmode="numeric"
      @update:value="onInput"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: number;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: number];
}>();

function onInput(val: number | null) {
  if (val == null || !Number.isFinite(val)) return;
  emit("update:modelValue", Math.min(100, Math.max(0, Math.round(val))));
}
</script>

<style scoped>
.percent-slider-field {
  display: flex;
  gap: 10px;
  width: 100%;
  align-items: center;
}

.percent-slider-field__input {
  width: 100%;
  max-width: 85px;
}

.percent-slider-field__slider {
  flex: 1;
  margin:2px;
}

</style>
