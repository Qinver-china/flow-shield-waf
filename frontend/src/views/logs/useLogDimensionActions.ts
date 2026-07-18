import { message } from "ant-design-vue";
import { useRouter } from "vue-router";
import {
  buildConditionsFromLogRule,
  buildConditionsFromStatsDimension,
  getResourceViewLabel,
  getResourceViewTarget,
  getResourceViewTargetFromLogRule,
  type LogResourceViewTarget,
  type StatsDimension,
} from "./constants";
import type { LogFilterState } from "./useLogFilterState";

export interface LogDimensionAction {
  key: string;
  label: string;
  onClick: () => void;
  divided?: boolean;
}

export function useLogDimensionActions() {
  const router = useRouter();

  function openResourceView(
    target: LogResourceViewTarget,
    onOpenDrawer: (target: LogResourceViewTarget) => void,
  ) {
    if (target.kind === "route") {
      router.push(target.path);
      return;
    }
    onOpenDrawer(target);
  }

  function buildStatsActions(options: {
    dimension: StatsDimension;
    itemKey: string;
    label: string;
    filterState: LogFilterState;
    onDrillDown: () => void;
    onOpenResource: (target: LogResourceViewTarget) => void;
  }): LogDimensionAction[] {
    const { dimension, itemKey, label, filterState, onDrillDown, onOpenResource } = options;
    if (!itemKey || itemKey === "none") return [];

    const actions: LogDimensionAction[] = [];
    const filterConditions = buildConditionsFromStatsDimension(dimension, itemKey);
    if (filterConditions.length) {
      actions.push({
        key: "add-filter",
        label: "添加到筛选",
        onClick: () => {
          filterState.addConditions(filterConditions);
          message.success("已添加到筛选");
        },
      });
    }

    const resourceTarget = getResourceViewTarget(dimension, itemKey, label);
    if (resourceTarget) {
      actions.push({
        key: "view-resource",
        label: getResourceViewLabel(dimension, itemKey),
        onClick: () => openResourceView(resourceTarget, onOpenResource),
      });
    }

    actions.push({
      key: "view-logs",
      label: "查看日志明细",
      divided: actions.length > 0,
      onClick: onDrillDown,
    });

    return actions;
  }

  function buildLogRuleActions(options: {
    record: {
      source?: string | null;
      rule_id?: number | null;
      rule_name?: string | null;
    };
    filterState: LogFilterState;
    onOpenResource: (target: LogResourceViewTarget) => void;
  }): LogDimensionAction[] {
    const { record, filterState, onOpenResource } = options;
    if (!record.rule_id) return [];

    const actions: LogDimensionAction[] = [];
    const filterConditions = buildConditionsFromLogRule(record);
    if (filterConditions.length) {
      actions.push({
        key: "add-filter",
        label: "添加到筛选",
        onClick: () => {
          filterState.addConditions(filterConditions);
          message.success("已添加到筛选");
        },
      });
    }

    const resourceTarget = getResourceViewTargetFromLogRule(record);
    if (resourceTarget) {
      actions.push({
        key: "view-resource",
        label: "查看当前规则",
        onClick: () => openResourceView(resourceTarget, onOpenResource),
      });
    }

    return actions;
  }

  return {
    buildStatsActions,
    buildLogRuleActions,
  };
}
