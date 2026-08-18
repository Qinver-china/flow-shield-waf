export { enabledFilterOptions, modeFilterOptions, exceptionScopeFilterOptions, certificateExpiryFilterOptions } from "./resourceList";

import { modeFilterOptions, exceptionScopeFilterOptions } from "./resourceList";
import type { BatchEditField } from "@/types/batch";

export const commonBatchEditFields = {
  enabled: {
    key: "enabled",
    label: "启用状态",
    type: "switch",
  } satisfies BatchEditField,
  siteIds: {
    key: "site_ids",
    label: "生效站点",
    type: "site_ids",
  } satisfies BatchEditField,
  mode: {
    key: "mode",
    label: "防护方式",
    type: "select",
    options: modeFilterOptions,
  } satisfies BatchEditField,
  priority: {
    key: "priority",
    label: "优先级",
    type: "number",
    min: 1,
  } satisfies BatchEditField,
  window: {
    key: "window",
    label: "时间窗口 (秒)",
    type: "number",
    min: 1,
  } satisfies BatchEditField,
  threshold: {
    key: "threshold",
    label: "阈值 (次)",
    type: "number",
    min: 1,
  } satisfies BatchEditField,
  scope: {
    key: "scope",
    label: "跳过范围",
    type: "select",
    options: exceptionScopeFilterOptions,
  } satisfies BatchEditField,
};

export const applyModeOptions = [
  { label: "仅建议", value: "suggest_only" },
  { label: "自动观察", value: "auto_observe" },
  { label: "自动分析并处理", value: "auto_handle" },
];
