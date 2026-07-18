<template>
  <span class="dimension-cell">
    <template v-if="actions.length">
      <a-dropdown :trigger="['click']" placement="bottomLeft">
        <a
          v-if="variant === 'link'"
          class="dimension-link"
          :title="label"
          @click.prevent
        >{{ label }}</a>
        <a-tag
          v-else
          :color="tagColor"
          class="dimension-tag"
          :title="label"
        >{{ label }}</a-tag>
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
    <template v-else>
      <a-tag v-if="variant === 'tag'" :color="tagColor" class="dimension-plain" :title="label">{{ label }}</a-tag>
      <span v-else class="dimension-plain" :title="label">{{ label }}</span>
    </template>
  </span>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import LogResourceViewDrawer from "./LogResourceViewDrawer.vue";
import type { LogResourceViewTarget, StatsDimension } from "./constants";
import type { LogFilterState } from "./useLogFilterState";
import { useLogDimensionActions, type LogDetailActionField } from "./useLogDimensionActions";

const props = withDefaults(
  defineProps<{
    label: string;
    filterState: LogFilterState;
    dimension?: StatsDimension;
    itemKey?: string;
    detailField?: LogDetailActionField;
    detailValue?: string;
    logRuleRecord?: {
      source?: string | null;
      rule_id?: number | null;
      rule_name?: string | null;
    };
    variant?: "link" | "tag";
    tagColor?: string;
  }>(),
  {
    variant: "link",
  },
);

const emit = defineEmits<{ "drill-down": [] }>();

const { buildStatsActions, buildLogDetailFieldActions, buildLogRuleActions } = useLogDimensionActions();
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

  if (props.detailField && props.detailValue) {
    return buildLogDetailFieldActions({
      field: props.detailField,
      value: props.detailValue,
      filterState: props.filterState,
      onOpenResource: onOpenResource,
    });
  }

  if (!props.dimension || !props.itemKey) return [];

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
.dimension-cell {
  display: inline;
}

.dimension-link {
  color: #1677ff;
  cursor: pointer;
}

.dimension-link:hover {
  color: #4096ff;
}

.dimension-tag {
  cursor: pointer;
}

.dimension-plain {
  color: inherit;
}

.log-dimension-menu {
  min-width: 156px;
}
</style>
