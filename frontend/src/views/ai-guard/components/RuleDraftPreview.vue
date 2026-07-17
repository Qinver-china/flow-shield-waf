<template>
  <div v-if="conditions" class="preview">
    <div class="label">规则条件预览</div>
    <condition-editor :value="conditions" readonly />
  </div>
</template>

<script setup lang="ts">
import ConditionEditor from "@/components/ConditionEditor.vue";

defineProps<{
  conditions: Record<string, unknown>;
}>();
</script>

<style scoped>
.preview {
  margin-top: 8px;
}
.label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}
</style>
