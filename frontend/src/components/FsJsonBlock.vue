<template>
  <div class="fs-json-block">
    <div class="fs-json-block__header">
      <h4 class="fs-json-block__title">{{ title }}</h4>
      <a-button type="link" size="small" class="fs-json-block__copy" @click="copy">
        <template #icon><CopyOutlined /></template>
        复制
      </a-button>
    </div>
    <pre class="fs-json-block__content">{{ content }}</pre>
  </div>
</template>

<script setup lang="ts">
import { CopyOutlined } from "@ant-design/icons-vue";
import { message } from "ant-design-vue";

const props = withDefaults(
  defineProps<{
    content: string;
    title?: string;
  }>(),
  { title: "JSON 数据" },
);

async function copy() {
  try {
    await navigator.clipboard.writeText(props.content);
    message.success("已复制");
  } catch {
    message.error("复制失败");
  }
}
</script>
