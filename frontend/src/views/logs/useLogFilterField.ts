import type { LogDetailFilters, LogFilterFieldDef } from "./constants";

const BOOL_SELECT_KEYS = new Set(["ip_is_private"]);

export function useLogFilterFieldBindings(filters: LogDetailFilters) {
  function getTextFilter(key: string) {
    return (filters as Record<string, string | undefined>)[key] ?? "";
  }

  function setTextFilter(key: string, value: string) {
    (filters as Record<string, string>)[key] = value ?? "";
  }

  function getSelectFilter(key: string) {
    return (filters as Record<string, string | undefined>)[key];
  }

  function setSelectFilter(key: string, value?: string) {
    (filters as Record<string, string | undefined>)[key] = value;
  }

  function getBoolFilter(key: string) {
    if (!BOOL_SELECT_KEYS.has(key)) return undefined;
    const value = (filters as Record<string, boolean | undefined>)[key];
    return value === undefined ? undefined : value ? "true" : "false";
  }

  function setBoolFilter(key: string, value?: string) {
    if (!BOOL_SELECT_KEYS.has(key)) return;
    (filters as Record<string, boolean | undefined>)[key] =
      value === undefined ? undefined : value === "true";
  }

  return {
    getTextFilter,
    setTextFilter,
    getSelectFilter,
    setSelectFilter,
    getBoolFilter,
    setBoolFilter,
  };
}

export function colSpanForField(field: LogFilterFieldDef, compact = false) {
  if (compact) {
    if (field.key === "keyword") return { span: 12, xl: 4 };
    if (field.type === "site") return { span: 12, xl: 3 };
    return { span: 12, xl: 2 };
  }
  if (field.key === "keyword") return { span: 12, xl: 8 };
  return { span: 12, xl: 4 };
}
