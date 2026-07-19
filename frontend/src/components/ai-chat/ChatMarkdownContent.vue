<template>
  <div class="chat-markdown" v-html="html" />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { renderChatMarkdown } from "@/utils/chatMarkdown";

const props = defineProps<{
  content: string;
}>();

const html = computed(() => renderChatMarkdown(props.content));
</script>

<style scoped>
.chat-markdown {
  line-height: 1.6;
  word-break: break-word;
}

.chat-markdown :deep(p) {
  margin: 0 0 0.75em;
}

.chat-markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.chat-markdown :deep(ul),
.chat-markdown :deep(ol) {
  margin: 0 0 0.75em;
  padding-left: 1.5em;
}

.chat-markdown :deep(li + li) {
  margin-top: 0.25em;
}

.chat-markdown :deep(pre) {
  margin: 0.75em 0;
  padding: 0.75em 1em;
  overflow-x: auto;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.06);
  font-size: 0.9em;
}

.chat-markdown :deep(code) {
  padding: 0.15em 0.35em;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.06);
  font-size: 0.9em;
}

.chat-markdown :deep(pre code) {
  padding: 0;
  background: transparent;
}

.chat-markdown :deep(blockquote) {
  margin: 0.75em 0;
  padding-left: 1em;
  border-left: 3px solid rgba(0, 0, 0, 0.15);
  color: rgba(0, 0, 0, 0.65);
}

.chat-markdown :deep(a) {
  color: #1677ff;
  text-decoration: none;
}

.chat-markdown :deep(a:hover) {
  text-decoration: underline;
}

.chat-markdown :deep(table) {
  width: 100%;
  margin: 0.75em 0;
  border-collapse: collapse;
  font-size: 0.9em;
}

.chat-markdown :deep(th),
.chat-markdown :deep(td) {
  padding: 0.4em 0.6em;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.chat-markdown :deep(th) {
  background: rgba(0, 0, 0, 0.04);
}

.chat-markdown :deep(hr) {
  margin: 1em 0;
  border: none;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.chat-markdown :deep(h1),
.chat-markdown :deep(h2),
.chat-markdown :deep(h3),
.chat-markdown :deep(h4) {
  margin: 1em 0 0.5em;
  line-height: 1.35;
}

.chat-markdown :deep(h1:first-child),
.chat-markdown :deep(h2:first-child),
.chat-markdown :deep(h3:first-child),
.chat-markdown :deep(h4:first-child),
.chat-markdown :deep(p:first-child) {
  margin-top: 0;
}
</style>
