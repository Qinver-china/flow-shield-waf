export type BatchEditFieldType = "switch" | "select" | "number" | "site_ids";

export interface BatchEditFieldOption {
  label: string;
  value: string | number | boolean;
}

export interface BatchEditField {
  key: string;
  label: string;
  type: BatchEditFieldType;
  options?: BatchEditFieldOption[];
  min?: number;
  placeholder?: string;
}

export interface BatchConfig {
  /** 是否启用批量操作，默认 true */
  enabled?: boolean;
  /** 是否允许批量删除，默认 true */
  allowDelete?: boolean;
  /** 是否支持启用/停用，默认根据表格列自动判断 */
  enableToggle?: boolean;
  /** 批量切换模式的选项；传入即启用该操作 */
  modeOptions?: BatchEditFieldOption[];
  /** 批量切换模式时的字段名，默认 mode */
  modeField?: string;
  /** 批量编辑可修改的字段 */
  editFields?: BatchEditField[];
}

export type BatchActionKey =
  | "edit"
  | "enable"
  | "disable"
  | "switch_mode"
  | "delete";
