import { computed, ref } from "vue";
import type { Dayjs } from "dayjs";
import { nowInAppTz, toAppTz, toUtcIso, formatDateTime } from "@/utils/datetime";
import { timePresets, type TimePreset } from "./constants";

export function resolveTimeRange(
  preset: TimePreset,
  customRange?: [Dayjs, Dayjs],
): { start: Dayjs; end: Dayjs } {
  const end = nowInAppTz();
  if (preset === "custom" && customRange?.length === 2) {
    return {
      start: toAppTz(customRange[0]),
      end: toAppTz(customRange[1]),
    };
  }
  const def = timePresets.find((item) => item.key === preset);
  if (def?.kind === "today") {
    return { start: end.startOf("day"), end };
  }
  if (def?.kind === "yesterday") {
    const yesterday = end.subtract(1, "day");
    return {
      start: yesterday.startOf("day"),
      end: yesterday.endOf("day"),
    };
  }
  const hours = def?.hours ?? 24;
  return { start: end.subtract(hours, "hour"), end };
}

export function useLogTimeRange(defaultPreset: TimePreset = "6h") {
  const preset = ref<TimePreset>(defaultPreset);
  const customRange = ref<[Dayjs, Dayjs]>();

  const range = computed(() => resolveTimeRange(preset.value, customRange.value));

  function toQueryParams() {
    const { start, end } = range.value;
    return {
      start: toUtcIso(start),
      end: toUtcIso(end),
    };
  }

  function rangeLabel() {
    const { start, end } = range.value;
    return `${start.format("YYYY-MM-DD HH:mm")} ~ ${end.format("YYYY-MM-DD HH:mm")}`;
  }

  return { preset, customRange, range, toQueryParams, rangeLabel };
}

export function formatTs(ts?: string | null) {
  return formatDateTime(ts);
}
