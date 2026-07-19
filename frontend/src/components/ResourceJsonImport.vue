<template>
  <fs-form-section
    v-if="!bare"
    title="JSON 导入"
    description="粘贴 JSON 后应用，将按当前资源类型保留有效字段、剔除多余字段并补齐默认值"
  >
    <a-textarea
      v-model:value="jsonText"
      :rows="5"
      class="fs-code-textarea"
      placeholder='例如：{"name": "示例规则", "enabled": true, ...}'
    />
    <div class="resource-json-import__actions">
      <a-button type="primary" ghost :disabled="!jsonText.trim()" @click="apply">
        应用导入
      </a-button>
      <a-button v-if="jsonText" @click="clear">清空</a-button>
    </div>
  </fs-form-section>
  <div v-else class="resource-json-import--bare">
    <p class="fs-hint">
      粘贴 JSON 后应用，将按当前资源类型保留有效字段、剔除多余字段并补齐默认值
    </p>
    <a-textarea
      v-model:value="jsonText"
      :rows="8"
      class="fs-code-textarea"
      placeholder='例如：{"name": "示例规则", "enabled": true, ...}'
    />
    <div class="resource-json-import__actions">
      <a-button type="primary" ghost :disabled="!jsonText.trim()" @click="apply">
        应用导入
      </a-button>
      <a-button v-if="jsonText" @click="clear">清空</a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { message } from "ant-design-vue";
import FsFormSection from "@/components/FsFormSection.vue";
import {
  normalizeImportedRecord,
  parseImportedRecordJson,
} from "@/utils/resourceRecordImport";

const props = withDefaults(
  defineProps<{
    defaultRecord: () => Record<string, unknown>;
    preserveId?: number | null;
    bare?: boolean;
  }>(),
  { bare: false },
);

const emit = defineEmits<{
  import: [Record<string, unknown>];
}>();

const jsonText = ref("");

function apply() {
  try {
    const parsed = parseImportedRecordJson(jsonText.value);
    const merged = normalizeImportedRecord(parsed, props.defaultRecord, {
      preserveId: props.preserveId,
    });
    emit("import", merged);
    message.success("已应用 JSON 导入");
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "导入失败");
  }
}

function clear() {
  jsonText.value = "";
}
</script>

<style scoped>
.resource-json-import__actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.resource-json-import--bare .fs-hint {
  margin: 0 0 12px;
}
</style>
