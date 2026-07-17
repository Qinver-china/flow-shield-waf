<template>
  <div class="template-hints">
    <div class="template-hints-title">可用变量（在内容中使用 <code>{变量名}</code> 占位）</div>
    <div class="template-vars">
      <a-tag
        v-for="item in variables"
        :key="item.key"
        class="var-tag"
        @click="emit('insert', item.key)"
      >
        <span class="var-key">{{ "{" + item.key + "}" }}</span>
        <span class="var-label">{{ item.label }}</span>
      </a-tag>
    </div>
    <div v-if="hint" class="template-hint">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
export interface TemplateVariable {
  key: string;
  label: string;
  description?: string;
}

defineProps<{
  variables: TemplateVariable[];
  hint?: string;
}>();

const emit = defineEmits<{
  insert: [key: string];
}>();
</script>

<style scoped>
.template-hints {
  margin-top: 8px;
}

.template-hints-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
}

.template-vars {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.var-tag {
  cursor: pointer;
  margin: 0;
  padding: 4px 8px;
  border-radius: 6px;
}

.var-key {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

.var-label {
  margin-left: 6px;
  color: #64748b;
  font-size: 12px;
}

.template-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
}

code {
  font-size: 12px;
}
</style>
