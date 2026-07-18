<template>
  <fs-hover-dropdown>
    <a class="name-link" :title="text" @click="onNameClick">{{ text }}</a>
    <template #overlay>
      <a-menu class="resource-name-menu" :selectable="false">
        <template v-for="(action, index) in actions" :key="action.key">
          <a-menu-divider v-if="action.divided && index > 0" />
          <a-menu-item :danger="action.danger" @click="() => runAction(action)">
            {{ action.label }}
          </a-menu-item>
        </template>
      </a-menu>
    </template>
  </fs-hover-dropdown>
</template>

<script setup lang="ts">
import FsHoverDropdown from "@/components/FsHoverDropdown.vue";
import type { ResourceQuickAction } from "@/composables/useResourceQuickActions";
import { useResourceQuickActions } from "@/composables/useResourceQuickActions";

const props = defineProps<{
  text: string;
  actions: ResourceQuickAction[];
}>();

const emit = defineEmits<{ view: [] }>();

const { runAction } = useResourceQuickActions();

function onNameClick() {
  emit("view");
}
</script>

<style scoped>
.name-link {
  color: var(--fs-color-primary);
  cursor: pointer;
}

.resource-name-menu {
  min-width: 148px;
}
</style>
