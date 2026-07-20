import { message } from "ant-design-vue";
import { useRouter } from "vue-router";
import { copyText } from "@/utils/clipboard";
import {
  buildConditionsFromLogRule,
  buildConditionsFromStatsDimension,
  buildResourceDrawerLocation,
  createFilterCondition,
  defaultOperatorForField,
  findLogFilterField,
  getResourceEditLabel,
  getResourceViewLabel,
  getResourceViewTarget,
  LOG_SOURCE_API,
  parseRuleStatsKey,
  type LogFilterCondition,
  type LogResourceViewTarget,
  type StatsDimension,
} from "./constants";
import type { LogFilterState } from "./useLogFilterState";

export type LogDetailActionField =
  | "domain"
  | "client_ip"
  | "method"
  | "request_uri"
  | "mode"
  | "source"
  | "blocked";

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
    if (target.kind === "api") {
      const location = buildResourceDrawerLocation(target.apiBase, target.id, "view");
      if (location) {
        router.push(location);
        return;
      }
    }
    onOpenDrawer(target);
  }

  function openResourceEdit(apiBase: string, id: number, source: string) {
    const location = buildResourceDrawerLocation(apiBase, id, "edit");
    if (!location) return;
    router.push(location);
  }

  function appendRuleResourceActions(
    actions: LogDimensionAction[],
    record: { source?: string | null; rule_id?: number | null; rule_name?: string | null },
  ) {
    if (!record.rule_id) return;
    const source = record.source || "rule";
    const apiBase = LOG_SOURCE_API[source];
    if (!apiBase) return;

    const key = record.source ? `${record.source}:${record.rule_id}` : String(record.rule_id);
    actions.push({
      key: "view-resource",
      label: getResourceViewLabel("rule_id", key),
      onClick: () => {
        const location = buildResourceDrawerLocation(apiBase, record.rule_id!, "view");
        if (location) router.push(location);
      },
    });
    actions.push({
      key: "edit-resource",
      label: getResourceEditLabel(source),
      onClick: () => openResourceEdit(apiBase, record.rule_id!, source),
    });
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

      if (dimension === "rule_id") {
        const parsed = parseRuleStatsKey(itemKey);
        if (parsed.ruleId) {
          const source = parsed.source || "rule";
          const apiBase = LOG_SOURCE_API[source];
          if (apiBase) {
            actions.push({
              key: "edit-resource",
              label: getResourceEditLabel(source),
              onClick: () => openResourceEdit(apiBase, parsed.ruleId!, source),
            });
          }
        }
      }

      if (dimension === "site_id") {
        const siteId = Number(itemKey);
        if (Number.isFinite(siteId)) {
          actions.push({
            key: "edit-resource",
            label: getResourceEditLabel("site"),
            onClick: () => openResourceEdit("/api/v1/sites", siteId, "site"),
          });
        }
      }
    }

    actions.push({
      key: "view-logs",
      label: "查看日志明细",
      divided: actions.length > 0,
      onClick: onDrillDown,
    });

    return actions;
  }

  function buildLogDetailFieldActions(options: {
    field: LogDetailActionField;
    value: string;
    filterState: LogFilterState;
    onOpenResource: (target: LogResourceViewTarget) => void;
  }): LogDimensionAction[] {
    const { field, value, filterState, onOpenResource } = options;
    if (!value) return [];

    const actions: LogDimensionAction[] = [];
    let filterConditions: LogFilterCondition[] = [];

    if (field === "request_uri") {
      const keywordField = findLogFilterField("keyword");
      if (keywordField) {
        filterConditions = [
          {
            ...createFilterCondition("keyword"),
            field: "keyword",
            operator: "contains",
            value,
          },
        ];
      }
    } else {
      filterConditions = buildConditionsFromStatsDimension(field as StatsDimension, value);
    }

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

    if (field === "source") {
      const resourceTarget = getResourceViewTarget("source", value, value);
      if (resourceTarget) {
        actions.push({
          key: "view-resource",
          label: getResourceViewLabel("source", value),
          onClick: () => openResourceView(resourceTarget, onOpenResource),
        });
      }
    }

    if (field === "client_ip" || field === "request_uri") {
      actions.push({
        key: "copy",
        label: "复制",
        divided: actions.length > 0,
        onClick: async () => {
          try {
            await copyText(value);
            message.success("已复制");
          } catch {
            message.error("复制失败");
          }
        },
      });
    }

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

    appendRuleResourceActions(actions, record);

    return actions;
  }

  return {
    buildStatsActions,
    buildLogDetailFieldActions,
    buildLogRuleActions,
  };
}
