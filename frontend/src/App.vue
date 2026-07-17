<template>
  <a-config-provider :theme="antdTheme">
    <router-view />
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { theme } from "ant-design-vue";
import { storeToRefs } from "pinia";
import { useThemeStore } from "@/stores/theme";

const themeStore = useThemeStore();
const { isDark } = storeToRefs(themeStore);

const antdTheme = computed(() => {
  const dark = isDark.value;
  return {
    algorithm: dark ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: {
      colorPrimary: "#2563eb",
      colorSuccess: "#22c55e",
      colorError: "#ef4444",
      colorWarning: "#f59e0b",
      colorInfo: "#0ea5e9",
      borderRadius: 8,
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
      colorBgContainer: dark ? "#0f172a" : "#ffffff",
      colorBgElevated: dark ? "#1e293b" : "#ffffff",
      colorBgLayout: dark ? "#020617" : "#f1f5f9",
      colorText: dark ? "#f8fafc" : "#0f172a",
      colorTextSecondary: dark ? "#cbd5e1" : "#475569",
      colorTextHeading: dark ? "#f8fafc" : "#0f172a",
      colorBorder: dark ? "#334155" : "#e2e8f0",
      colorBorderSecondary: dark ? "#334155" : "#e2e8f0",
      colorFillAlter: dark ? "#1e293b" : "#f8fafc",
      colorFillContent: dark ? "#334155" : "#e2e8f0",
      colorFillSecondary: dark ? "#334155" : "#e2e8f0",
    },
    components: {
      Layout: {
        bodyBg: dark ? "#020617" : "#f1f5f9",
        headerBg: dark ? "#0f172a" : "#ffffff",
        siderBg: dark ? "#020617" : "#081a3d",
      },
      Card: {
        colorBgContainer: dark ? "#0f172a" : "#ffffff",
      },
      Table: {
        colorBgContainer: dark ? "#0f172a" : "#ffffff",
        headerBg: dark ? "#1e293b" : "#f8fafc",
        headerColor: dark ? "#f8fafc" : "#0f172a",
        rowHoverBg: dark ? "#1a1e2f" : "#f1f5f9",
        rowSelectedBg: dark ? "#1e3a5f" : "#eff6ff",
        rowSelectedHoverBg: dark ? "#1e40af" : "#dbeafe",
        headerSortActiveBg: dark ? "#334155" : "#e2e8f0",
        headerSortHoverBg: dark ? "#334155" : "#e2e8f0",
        borderColor: dark ? "#334155" : "#e2e8f0",
        footerBg: dark ? "#1e293b" : "#f8fafc",
        footerColor: dark ? "#f8fafc" : "#0f172a",
        colorTextHeading: dark ? "#f8fafc" : "#0f172a",
      },
      Modal: {
        contentBg: dark ? "#0f172a" : "#ffffff",
        headerBg: dark ? "#0f172a" : "#ffffff",
      },
      Drawer: {
        colorBgElevated: dark ? "#0f172a" : "#ffffff",
      },
      Menu: {
        darkItemBg: "#081a3d",
        darkSubMenuItemBg: "#081a3d",
        darkItemColor: "rgba(255, 255, 255, 0.72)",
        darkItemHoverColor: "#f8fafc",
        darkItemHoverBg: "rgba(255, 255, 255, 0.08)",
        darkItemSelectedBg: "#2563eb",
        darkItemSelectedColor: "#ffffff",
        darkGroupTitleColor: "rgba(255, 255, 255, 0.45)",
      },
    },
  };
});
</script>
