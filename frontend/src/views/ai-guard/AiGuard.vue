<template>
  <page-shell title="AI 防护" description="智能助手对话、自动防护策略与 AI 分析记录">
    <template #actions>
      <a-button
        v-if="tab === 'policies'"
        type="primary"
        @click="policiesRef?.openCreate()"
      >
        新增防护策略
      </a-button>
    </template>

    <a-tabs v-model:active-key="tab" size="large" class="ai-guard-tabs fs-tabs-animated">
      <a-tab-pane key="chat" tab="AI智能助手" />
      <a-tab-pane key="policies" tab="AI防护策略" />
      <a-tab-pane key="incidents" tab="AI分析记录" />
      <a-tab-pane key="settings" tab="AI 配置" />
    </a-tabs>

    <fs-slide-transition :transition-key="tab">
      <chat-tab v-if="tab === 'chat'" />
      <defense-policies-tab v-else-if="tab === 'policies'" ref="policiesRef" />
      <incidents-tab v-else-if="tab === 'incidents'" />
      <settings-tab v-else-if="tab === 'settings'" />
    </fs-slide-transition>
  </page-shell>
</template>

<script setup lang="ts">
import { ref } from "vue";
import FsSlideTransition from "@/components/FsSlideTransition.vue";
import PageShell from "@/components/PageShell.vue";
import ChatTab from "./tabs/ChatTab.vue";
import DefensePoliciesTab from "./tabs/DefensePoliciesTab.vue";
import IncidentsTab from "./tabs/IncidentsTab.vue";
import SettingsTab from "./tabs/SettingsTab.vue";

const tab = ref("chat");
const policiesRef = ref<InstanceType<typeof DefensePoliciesTab> | null>(null);
</script>

<style scoped>
.ai-guard-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 0;
}

@media (max-width: 767px) {
  .ai-guard-tabs :deep(.ant-tabs-nav-wrap) {
    overflow: visible;
  }

  .ai-guard-tabs :deep(.ant-tabs-nav-list) {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .ai-guard-tabs :deep(.ant-tabs-nav-list::-webkit-scrollbar) {
    display: none;
  }

  .ai-guard-tabs :deep(.ant-tabs-tab) {
    flex-shrink: 0;
  }
}
</style>
