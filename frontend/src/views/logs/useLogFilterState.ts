import { computed, ref } from "vue";
import type { Dayjs } from "dayjs";
import type { LocationQuery } from "vue-router";
import {
  applyStatsDrillDownToFilters,
  buildLogQueryParams,
  buildConditionsFromStatsDimension,
  conditionsToFiltersJson,
  conditionsToLogDetailFilters,
  createDefaultLogFilters,
  createFilterCondition,
  formatConditionLabel,
  isConditionComplete,
  logDetailFiltersToConditions,
  type LogFilterCondition,
  type StatsDimension,
  type TimePreset,
} from "./constants";
import { useLogTimeRange } from "./useLogTimeRange";
import { toAppTz } from "@/utils/datetime";
import type { LogDrillDownFilter } from "./LogStatsTab.vue";

let sharedFilterState: LogFilterState | null = null;

function createLogFilterState(defaultPreset: TimePreset) {
  const { preset, customRange, range, toQueryParams, rangeLabel } = useLogTimeRange(defaultPreset);
  const appliedConditions = ref<LogFilterCondition[]>([]);
  const draftConditions = ref<LogFilterCondition[]>([]);
  const editorOpen = ref(false);
  const refreshToken = ref(0);

  const hasAppliedFilters = computed(() => appliedConditions.value.length > 0);
  const appliedFilterLabels = computed(() =>
    appliedConditions.value.map((condition) => formatConditionLabel(condition)),
  );

  const detailFilters = computed(() => conditionsToLogDetailFilters(appliedConditions.value));

  function cloneConditions(conditions: LogFilterCondition[]) {
    return conditions.map((item) => ({
      ...item,
      value: Array.isArray(item.value) ? [...item.value] : item.value,
    }));
  }

  function closeEditorAndSyncDraft() {
    draftConditions.value = appliedConditions.value.length
      ? cloneConditions(appliedConditions.value)
      : [createFilterCondition()];
    editorOpen.value = false;
  }

  function openEditor(seed?: LogFilterCondition[]) {
    draftConditions.value = seed?.length ? cloneConditions(seed) : [createFilterCondition()];
    editorOpen.value = true;
  }

  function closeEditor() {
    editorOpen.value = false;
  }

  function addDraftCondition() {
    draftConditions.value.push(createFilterCondition());
  }

  function removeDraftCondition(id: string) {
    draftConditions.value = draftConditions.value.filter((item) => item.id !== id);
    if (!draftConditions.value.length) {
      draftConditions.value = [createFilterCondition()];
    }
  }

  function applyDraft() {
    appliedConditions.value = draftConditions.value.filter(isConditionComplete);
    editorOpen.value = false;
    refreshToken.value += 1;
  }

  function clearAppliedFilters() {
    appliedConditions.value = [];
    closeEditorAndSyncDraft();
    refreshToken.value += 1;
  }

  function resetAll() {
    preset.value = defaultPreset;
    customRange.value = undefined;
    appliedConditions.value = [];
    draftConditions.value = [createFilterCondition()];
    editorOpen.value = false;
    refreshToken.value += 1;
  }

  function applyDrillDown(payload: LogDrillDownFilter) {
    preset.value = "custom";
    customRange.value = [toAppTz(payload.start), toAppTz(payload.end)];
    const filters = createDefaultLogFilters();
    applyStatsDrillDownToFilters(payload.dimension as StatsDimension, payload.key, filters);
    appliedConditions.value = logDetailFiltersToConditions(filters);
    refreshToken.value += 1;
  }

  function buildSharedQueryParams(extra?: Record<string, unknown>) {
    return {
      preset: preset.value,
      ...toQueryParams(),
      filters: conditionsToFiltersJson(appliedConditions.value),
      ...extra,
    };
  }

  function buildDetailQueryParams(paging: { page: number; page_size: number }) {
    return buildLogQueryParams(detailFilters.value, paging, toQueryParams(), appliedConditions.value);
  }

  function setPreset(next: TimePreset, options?: { silent?: boolean }) {
    preset.value = next;
    if (next !== "custom") {
      customRange.value = undefined;
    }
    if (!options?.silent) {
      refreshToken.value += 1;
    }
  }

  function queryValue(query: LocationQuery, key: string) {
    const value = query[key];
    if (Array.isArray(value)) return value[0];
    return value;
  }

  function applyFromRouteQuery(query: LocationQuery) {
    let changed = false;

    const nextPreset = queryValue(query, "preset") as TimePreset | undefined;
    if (nextPreset && nextPreset !== preset.value) {
      setPreset(nextPreset, { silent: true });
      changed = true;
    }

    const filters = createDefaultLogFilters();
    let hasFilter = false;

    const blocked = queryValue(query, "blocked");
    if (blocked === "true") {
      filters.blocked = true;
      hasFilter = true;
    } else if (blocked === "false") {
      filters.blocked = false;
      hasFilter = true;
    }

    const detailKeys = [
      "source",
      "mode",
      "log_type",
      "client_ip",
      "rule_id",
      "site_id",
      "bot_name",
      "bot_category",
      "geo_country",
      "method",
      "keyword",
    ] as const;

    for (const key of detailKeys) {
      const value = queryValue(query, key);
      if (!value) continue;
      if (key === "rule_id" || key === "site_id") {
        filters[key] = Number(value);
      } else {
        (filters as Record<string, string | number | undefined>)[key] = value;
      }
      hasFilter = true;
    }

    // Always rebuild from route query when any filter key is present; otherwise
    // clear sticky conditions left by a previous navigation (keep-alive singleton).
    const nextConditions = hasFilter ? logDetailFiltersToConditions(filters) : [];
    const nextKey = JSON.stringify(nextConditions);
    const currentKey = JSON.stringify(appliedConditions.value);
    if (nextKey !== currentKey) {
      appliedConditions.value = nextConditions;
      changed = true;
    }

    if (changed) {
      refreshToken.value += 1;
    }
  }

  function setCustomRange(next?: [Dayjs, Dayjs]) {
    customRange.value = next;
    if (next?.length === 2) {
      preset.value = "custom";
      refreshToken.value += 1;
    }
  }

  function bumpRefresh() {
    refreshToken.value += 1;
  }

  function removeAppliedCondition(index: number) {
    const next = [...appliedConditions.value];
    next.splice(index, 1);
    appliedConditions.value = next;
    closeEditorAndSyncDraft();
    refreshToken.value += 1;
  }

  function addConditions(conditions: LogFilterCondition[]) {
    if (!conditions.length) return;
    appliedConditions.value = [...appliedConditions.value, ...conditions];
    refreshToken.value += 1;
  }

  function addConditionsFromStats(dimension: StatsDimension, key: string) {
    addConditions(buildConditionsFromStatsDimension(dimension, key));
  }

  return {
    preset,
    customRange,
    range,
    toQueryParams,
    rangeLabel,
    appliedConditions,
    draftConditions,
    editorOpen,
    refreshToken,
    hasAppliedFilters,
    appliedFilterLabels,
    detailFilters,
    openEditor,
    closeEditor,
    addDraftCondition,
    removeDraftCondition,
    applyDraft,
    clearAppliedFilters,
    resetAll,
    applyDrillDown,
    buildSharedQueryParams,
    buildDetailQueryParams,
    setPreset,
    setCustomRange,
    bumpRefresh,
    removeAppliedCondition,
    applyFromRouteQuery,
    addConditions,
    addConditionsFromStats,
  };
}

export function useLogFilterState(defaultPreset: TimePreset = "6h") {
  if (!sharedFilterState) {
    sharedFilterState = createLogFilterState(defaultPreset);
  }
  return sharedFilterState;
}

export type LogFilterState = ReturnType<typeof createLogFilterState>;
