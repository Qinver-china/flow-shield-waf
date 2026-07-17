export interface Field {
  key: string;
  label: string;
  requires_arg: boolean;
  operators: string[];
  value_type: string;
  options?: { value: string; label: string }[];
  compare_modes?: { value: string; label: string }[];
}

export interface Category {
  name: string;
  fields: Field[];
}

export interface UiLeaf {
  kind: "leaf";
  field?: string;
  arg?: string;
  op?: string;
  valueText: string;
  valueList: string[];
  valueNumber: number | null;
  trafficWindow?: number;
  trafficCompare?: string;
  trafficThreshold?: number | null;
  trafficPercent?: number | null;
}

export interface UiGroup {
  kind: "group";
  logic: string;
  conditions: ConditionNode[];
}

export type ConditionNode = UiLeaf | UiGroup;

export const NO_VALUE_OPS = ["is_empty", "exists", "key_exists", "key_absent"];
export const LIST_OPS = ["in_list", "not_in", "in_cidr", "geo_in", "between"];
export const IP_GROUP_OPS = ["in_ip_group", "not_in_ip_group"];
export const NUMBER_OPS = ["len_gt", "len_lt"];
export const TRAFFIC_FIELD = "traffic.global";
export const TRAFFIC_BASELINE_COMPARES = ["baseline_gt", "baseline_lt"];
export const MAX_GROUP_DEPTH = 10;

export function isTrafficField(fieldKey?: string) {
  return fieldKey === TRAFFIC_FIELD;
}

export function isTrafficBaselineCompare(compare?: string) {
  return !!compare && TRAFFIC_BASELINE_COMPARES.includes(compare);
}

export function emptyLeaf(): UiLeaf {
  return {
    kind: "leaf",
    field: undefined,
    arg: "",
    op: undefined,
    valueText: "",
    valueList: [],
    valueNumber: null,
    trafficWindow: 300,
    trafficCompare: "abs_gt",
    trafficThreshold: 1000,
    trafficPercent: 50,
  };
}

export function emptyGroup(logic = "and"): UiGroup {
  return { kind: "group", logic, conditions: [] };
}

function parseLeaf(node: any): UiLeaf {
  const leaf = emptyLeaf();
  leaf.field = node.field;
  leaf.arg = node.arg;
  leaf.op = node.op;

  if (isTrafficField(node.field) && node.op === "compare" && node.value && typeof node.value === "object") {
    leaf.trafficWindow = Number(node.value.window_sec) || 300;
    leaf.trafficCompare = node.value.compare || "abs_gt";
    if (isTrafficBaselineCompare(leaf.trafficCompare)) {
      leaf.trafficPercent = Number(node.value.percent ?? 50);
    } else {
      leaf.trafficThreshold = Number(node.value.threshold ?? 0);
    }
    return leaf;
  }

  const valueList = Array.isArray(node.value)
    ? node.value.map((item: unknown) => String(item))
    : node.value != null && node.value !== ""
      ? [String(node.value)]
      : [];
  leaf.valueText = Array.isArray(node.value) ? node.value.join(",") : (node.value ?? "");
  leaf.valueList = valueList;
  leaf.valueNumber =
    NUMBER_OPS.includes(node.op) && node.value != null && node.value !== ""
      ? Number(node.value)
      : null;
  return leaf;
}

export function parseConditionNode(node: any): ConditionNode {
  if (node && typeof node === "object" && "conditions" in node) {
    return {
      kind: "group",
      logic: node.logic || "and",
      conditions: (node.conditions || []).map(parseConditionNode),
    };
  }
  return parseLeaf(node);
}

export function parseConditionTree(value: any): UiGroup {
  if (!value) return emptyGroup();
  if (value.field) {
    return { kind: "group", logic: "and", conditions: [parseLeaf(value)] };
  }
  return {
    kind: "group",
    logic: value.logic || "and",
    conditions: (value.conditions || []).map(parseConditionNode),
  };
}

export function serializeLeaf(row: UiLeaf, fieldMap: Record<string, Field>): any | null {
  if (!row.field) return null;

  if (isTrafficField(row.field)) {
    if (!row.trafficWindow || !row.trafficCompare) return null;
    const value: Record<string, unknown> = {
      window_sec: row.trafficWindow,
      compare: row.trafficCompare,
    };
    if (isTrafficBaselineCompare(row.trafficCompare)) {
      value.percent = row.trafficPercent ?? 0;
    } else {
      value.threshold = row.trafficThreshold ?? 0;
    }
    return { field: row.field, op: "compare", value };
  }

  if (!row.op) return null;
  const out: any = { field: row.field, op: row.op };
  if (fieldMap[row.field]?.requires_arg && row.arg) out.arg = row.arg;
  if (!NO_VALUE_OPS.includes(row.op)) {
    if (IP_GROUP_OPS.includes(row.op)) {
      out.value = (row.valueList || [])
        .map((item) => Number(item))
        .filter((n) => Number.isFinite(n) && n > 0);
    } else if (LIST_OPS.includes(row.op)) {
      out.value = (row.valueList || []).filter(Boolean);
    } else if (NUMBER_OPS.includes(row.op)) {
      out.value = row.valueNumber;
    } else {
      out.value = row.valueText;
    }
  }
  return out;
}

export function serializeNode(node: ConditionNode, fieldMap: Record<string, Field>): any | null {
  if (node.kind === "group") {
    const conditions = node.conditions
      .map((child) => serializeNode(child, fieldMap))
      .filter(Boolean);
    return { logic: node.logic, conditions };
  }
  return serializeLeaf(node, fieldMap);
}

export function serializeTree(group: UiGroup, fieldMap: Record<string, Field>) {
  const serialized = serializeNode(group, fieldMap);
  return serialized || { logic: "and", conditions: [] };
}

export function opsFor(fieldMap: Record<string, Field>, fieldKey?: string): string[] {
  return fieldKey ? fieldMap[fieldKey]?.operators || [] : [];
}

export function optionsFor(fieldMap: Record<string, Field>, fieldKey?: string) {
  return fieldKey ? fieldMap[fieldKey]?.options || [] : [];
}

export function compareModesFor(fieldMap: Record<string, Field>, fieldKey?: string) {
  return fieldKey ? fieldMap[fieldKey]?.compare_modes || [] : [];
}

export function hasOptions(fieldMap: Record<string, Field>, fieldKey?: string) {
  return !!fieldKey && optionsFor(fieldMap, fieldKey).length > 0;
}

export function isIpGroupOp(op?: string) {
  return !!op && IP_GROUP_OPS.includes(op);
}

export function isListOp(op?: string) {
  return !!op && LIST_OPS.includes(op);
}

export function isNumberOp(op?: string) {
  return !!op && NUMBER_OPS.includes(op);
}

export function onFieldChange(row: UiLeaf, fieldMap: Record<string, Field>) {
  if (isTrafficField(row.field)) {
    row.op = "compare";
    row.trafficWindow = row.trafficWindow ?? 300;
    row.trafficCompare = row.trafficCompare ?? "abs_gt";
    row.trafficThreshold = row.trafficThreshold ?? 1000;
    row.trafficPercent = row.trafficPercent ?? 50;
    return;
  }
  const ops = opsFor(fieldMap, row.field);
  if (row.op && !ops.includes(row.op)) row.op = ops[0];
  row.valueText = "";
  row.valueList = [];
  row.valueNumber = null;
}

export function onOpChange(row: UiLeaf, fieldMap: Record<string, Field>) {
  if (isTrafficField(row.field)) {
    row.op = "compare";
    return;
  }
  if (isListOp(row.op)) {
    if (!row.valueList?.length) {
      if (row.valueText) row.valueList = [String(row.valueText)];
      else if (row.valueNumber != null) row.valueList = [String(row.valueNumber)];
    }
    row.valueText = "";
    row.valueNumber = null;
    return;
  }
  if (isIpGroupOp(row.op)) {
    if (!row.valueList?.length && row.valueText) {
      row.valueList = [String(row.valueText)];
    }
    row.valueText = "";
    row.valueNumber = null;
    return;
  }
  if (isNumberOp(row.op)) {
    if (row.valueNumber == null) {
      if (row.valueText !== "") {
        const n = Number(row.valueText);
        row.valueNumber = Number.isFinite(n) ? n : null;
      } else if (row.valueList?.length) {
        const n = Number(row.valueList[0]);
        row.valueNumber = Number.isFinite(n) ? n : null;
      }
    }
    row.valueText = "";
    row.valueList = [];
    return;
  }
  if (hasOptions(fieldMap, row.field)) {
    row.valueText = row.valueList?.[0] || row.valueText || "";
  } else if (row.valueList?.length) {
    row.valueText = row.valueList.join(",");
  } else if (row.valueNumber != null) {
    row.valueText = String(row.valueNumber);
  }
  row.valueList = [];
  row.valueNumber = null;
}

export function formatOptionLabel(
  fieldMap: Record<string, Field>,
  fieldKey: string,
  value: string,
) {
  const opt = optionsFor(fieldMap, fieldKey).find((o) => o.value === String(value));
  return opt?.label || value;
}

export function displayLeafValue(
  row: UiLeaf,
  fieldMap: Record<string, Field>,
  ipGroupLabel?: (id: string) => string,
): string | null {
  if (isTrafficField(row.field)) {
    const win = optionsFor(fieldMap, row.field).find(
      (o) => Number(o.value) === row.trafficWindow,
    );
    const cmp = compareModesFor(fieldMap, row.field).find(
      (o) => o.value === row.trafficCompare,
    );
    const parts = [win?.label || `${row.trafficWindow} 秒`];
    parts.push(cmp?.label || row.trafficCompare || "-");
    if (isTrafficBaselineCompare(row.trafficCompare)) {
      parts.push(`${row.trafficPercent ?? 0}%`);
    } else {
      parts.push(String(row.trafficThreshold ?? 0));
    }
    return parts.join(" · ");
  }
  if (!row.op || NO_VALUE_OPS.includes(row.op)) return null;
  if (isListOp(row.op)) {
    const items = row.valueList?.length ? row.valueList : [];
    if (!items.length) return row.valueText || "-";
    return items.map((v) => formatOptionLabel(fieldMap, row.field!, v)).join("、");
  }
  if (isIpGroupOp(row.op)) {
    const items = row.valueList?.length ? row.valueList : [];
    if (!items.length) return "-";
    const label = ipGroupLabel || ((id: string) => id);
    return items.map((v) => label(String(v))).join("、");
  }
  if (isNumberOp(row.op)) {
    return row.valueNumber != null ? String(row.valueNumber) : row.valueText || "-";
  }
  if (hasOptions(fieldMap, row.field)) {
    return formatOptionLabel(fieldMap, row.field!, row.valueText) || "-";
  }
  return row.valueText || "-";
}

export function formatLeafRow(
  row: UiLeaf,
  fieldMap: Record<string, Field>,
  operators: Record<string, string>,
  ipGroupLabel?: (id: string) => string,
): string {
  const fieldLabel = fieldMap[row.field || ""]?.label || row.field || "-";
  if (isTrafficField(row.field)) {
    const val = displayLeafValue(row, fieldMap, ipGroupLabel);
    return [fieldLabel, val].filter(Boolean).join(" · ");
  }
  const opLabel = operators[row.op || ""] || row.op || "-";
  const parts = [fieldLabel];
  if (row.arg) parts.push(`子键: ${row.arg}`);
  parts.push(opLabel);
  const val = displayLeafValue(row, fieldMap, ipGroupLabel);
  if (val !== null) parts.push(`值: ${val}`);
  return parts.join(" · ");
}

export function logicLabel(logic: string) {
  return logic === "or" ? "任一 (OR)" : "全部 (AND)";
}
