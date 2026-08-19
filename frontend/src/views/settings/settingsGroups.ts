import type { Component } from "vue";
import {
  ApiOutlined,
  CloudUploadOutlined,
  FileTextOutlined,
  NotificationOutlined,
  SafetyOutlined,
  UserOutlined,
} from "@ant-design/icons-vue";

export type SettingsGroupKey =
  | "account-display"
  | "engine-protection"
  | "visitor-pages"
  | "logging-notify"
  | "panels-channels"
  | "integration-backup";

export interface SettingsNavItem {
  key: SettingsGroupKey;
  label: string;
  shortLabel: string;
  icon: Component;
}

export const SETTINGS_NAV_ITEMS: SettingsNavItem[] = [
  { key: "account-display", label: "账户与显示", shortLabel: "账户", icon: UserOutlined },
  { key: "engine-protection", label: "引擎与防护", shortLabel: "引擎", icon: SafetyOutlined },
  { key: "visitor-pages", label: "访客页面", shortLabel: "页面", icon: FileTextOutlined },
  { key: "logging-notify", label: "日志采样", shortLabel: "日志", icon: NotificationOutlined },
  { key: "panels-channels", label: "面板与通道", shortLabel: "通道", icon: ApiOutlined },
  { key: "integration-backup", label: "配置备份", shortLabel: "备份", icon: CloudUploadOutlined },
];

export const LEGACY_TAB_ALIASES: Record<string, SettingsGroupKey> = {
  account: "account-display",
  display: "account-display",
  engine: "engine-protection",
  challenge: "engine-protection",
  debug: "engine-protection",
  "response-pages": "visitor-pages",
  logging: "logging-notify",
  notify: "panels-channels",
  panels: "panels-channels",
  channels: "panels-channels",
  backup: "integration-backup",
};

export const LEGACY_TABS = new Set(Object.keys(LEGACY_TAB_ALIASES));

export function groupFromLegacyTab(tab: string | undefined | null): SettingsGroupKey {
  if (!tab) return "account-display";
  if (tab in LEGACY_TAB_ALIASES) return LEGACY_TAB_ALIASES[tab];
  const groups = new Set(Object.values(LEGACY_TAB_ALIASES));
  if (groups.has(tab as SettingsGroupKey)) return tab as SettingsGroupKey;
  return "account-display";
}

export function legacyTabForGroup(group: SettingsGroupKey): string {
  switch (group) {
    case "account-display":
      return "account";
    case "engine-protection":
      return "engine";
    case "visitor-pages":
      return "response-pages";
    case "logging-notify":
      return "logging";
    case "panels-channels":
      return "panels";
    case "integration-backup":
      return "panels";
    default:
      return "account";
  }
}
