<template>
  <fs-form-section :title="title" :description="description">
    <div class="fs-switch-row">
      <span>{{ switchLabel }}</span>
      <a-switch v-model:checked="record.custom_block_page_enabled" :disabled="readonly" />
    </div>
    <template v-if="record.custom_block_page_enabled">
      <a-row :gutter="16">
        <a-col :span="8">
          <a-form-item label="响应状态码">
            <a-select
              v-model:value="record.block_page_status_code"
              :disabled="readonly"
              :options="BLOCK_STATUS_OPTIONS"
            />
          </a-form-item>
        </a-col>
      </a-row>
      <a-form-item label="HTML 内容">
        <a-textarea
          v-model:value="record.block_page_html"
          :rows="10"
          :disabled="readonly"
          class="fs-code-textarea"
        />
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
    title: "自定义拦截响应",
    description: "关闭时使用站点或全局防护页面；命中本规则时优先使用此处配置",
    switchLabel: "启用规则专属拦截页",
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
