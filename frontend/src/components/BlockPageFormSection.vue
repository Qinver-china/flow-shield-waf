<template>
  <fs-form-section :title="title">
    <div class="fs-switch-row">
      <div>
        <div><b>{{ switchLabel }}</b></div>
        <div class="fs-muted" v-if="description">{{ description }}</div>
      </div>
      <a-switch v-model:checked="record.custom_block_page_enabled" :disabled="readonly" />
    </div>
    <template v-if="record.custom_block_page_enabled">
      <a-form-item label="响应状态码">
        <a-select v-model:value="record.block_page_status_code" :disabled="readonly" :options="BLOCK_STATUS_OPTIONS" />
      </a-form-item>
      <a-form-item label="HTML 内容">
        <a-textarea v-model:value="record.block_page_html" :rows="10" :disabled="readonly" class="fs-code-textarea" />
      </a-form-item>
      <page-template-hints :variables="templateVariables" />
    </template>
  </fs-form-section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import FsFormSection from "@/components/FsFormSection.vue";
import PageTemplateHints, { type TemplateVariable } from "@/components/PageTemplateHints.vue";
import { api } from "@/api";
import { BLOCK_STATUS_OPTIONS } from "@/constants/blockPage";

withDefaults(
  defineProps<{
    record: Record<string, unknown>;
    readonly?: boolean;
    title?: string;
    description?: string;
    switchLabel?: string;
  }>(),
  {
    readonly: false,
    title: "自定义拦截响应页面",
    description: "",
    switchLabel: "",
  },
);

const templateVariables = ref<TemplateVariable[]>([]);

onMounted(async () => {
  try {
    const resp = await api.get<{ template_variables: TemplateVariable[] }>("/api/v1/settings/block-page");
    templateVariables.value = resp.data.template_variables || [];
  } catch {
    templateVariables.value = [];
  }
});
</script>

<style scoped>
.fs-switch-row {
  margin-bottom: 16px;
}
</style>