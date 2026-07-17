import { computed, ref } from "vue";
import type { Dayjs } from "dayjs";
import { nowInAppTz, toAppTz, toUtcIso, formatDateTime } from "@/utils/datetime";
import { timePresets, type TimePreset } from "./constants";

export function useLogTimeRange(defaultPreset: TimePreset = "24h") {
  const preset = ref<TimePreset>(defaultPreset);
  const customRange = ref<[Dayjs, Dayjs]>();

  const range = computed(() => {
    if (preset.value === "custom" && customRange.value?.length === 2) {
      return {
        start: toAppTz(customRange.value[0]),
        end: toAppTz(customRange.value[1]),
      };
    }
    const end = nowInAppTz();
    const hours = timePresets.find((p) => p.key === preset.value)?.hours ?? 24;
    return { start: end.subtract(hours, "hour"), end };
  });

  function toQueryParams() {
    const { start, end } = range.value;
    return {
      start: toUtcIso(start),
      end: toUtcIso(end),
    };
  }

  function rangeLabel() {
    const { start, end } = range.value;
    return `${start.format("MM-DD HH:mm")} ~ ${end.format("MM-DD HH:mm")}`;
  }

  return { preset, customRange, range, toQueryParams, rangeLabel };
}

export function formatTs(ts?: string | null) {
  return formatDateTime(ts);
}
