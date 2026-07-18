<template>
  <template v-if="actions.length">
    <a-dropdown :trigger="['click']" placement="bottomLeft">
      <a class="dimension-link" :title="label" @click.prevent>{{ label }}</a>
      <template #overlay>
        <a-menu class="log-dimension-menu" :selectable="false">
          <template v-for="(action, index) in actions" :key="action.key">
            <a-menu-divider v-if="action.divided && index > 0" />
            <a-menu-item @click="action.onClick">{{ action.label }}</a-menu-item>
          </template>
        </a-menu>
      </template>
    </a-dropdown>
    <log-resource-view-drawer v-model:open="resourceOpen" :target="resourceTarget" />
  </template>
  <span v-else class="dimension-plain" :title="label">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import LogResourceViewDrawer from "./LogResourceViewDrawer.vue";
import type { LogResourceViewTarget, StatsDimension } from "./constants";
import type { LogFilterState } from "./useLogFilterState";
import { useLogDimensionActions } from "./useLogDimensionActions";

const props = defineProps<{
  label: string;
  dimension: StatsDimension;
  itemKey: string;
  filterState: LogFilterState;
  logRuleRecord?: {
    source?: string | null;
    rule_id?: number | null;
    rule_name?: string | null;
  };
}>();

const emit = defineEmits<{ "drill-down": [] }>();

const { buildStatsActions, buildLogRuleActions } = useLogDimensionActions();
const resourceOpen = ref(false);
const resourceTarget = ref<LogResourceViewTarget | null>(null);

function onOpenResource(target: LogResourceViewTarget) {
  resourceTarget.value = target;
  resourceOpen.value = true;
}

const actions = computed(() => {
  if (props.logRuleRecord) {
    return buildLogRuleActions({
      record: props.logRuleRecord,
      filterState: props.filterState,
      onOpenResource: onOpenResource,
    });
  }

  return buildStatsActions({
    dimension: props.dimension,
    itemKey: props.itemKey,
    label: props.label,
    filterState: props.filterState,
    onDrillDown: () => emit("drill-down"),
    onOpenResource: onOpenResource,
  });
});
</script>

<style scoped>
.dimension-link {
  color: #1677ff;
  cursor: pointer;
}

.dimension-link:hover {
  color: #4096ff;
}

.dimension-plain {
  color: inherit;
}

.log-dimension-menu {
  min-width: 156px;
}
</style>
