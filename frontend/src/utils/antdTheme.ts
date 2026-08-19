import { theme } from "ant-design-vue";
import type { ThemeConfig } from "ant-design-vue/es/config-provider/context";

/** Resolve a CSS custom property from `:root` / `[data-theme]`. */
function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Parse a CSS length token (e.g. `8px`) into a number for Ant Design. */
function cssVarPx(name: string, fallback = 8): number {
  const n = Number.parseFloat(cssVar(name));
  return Number.isFinite(n) ? n : fallback;
}

/**
 * Build Ant Design theme from `--fs-*` design tokens.
 * Must run after `data-theme` is applied so light/dark values resolve correctly.
 */
export function buildAntdTheme(isDark: boolean): ThemeConfig {
  const v = cssVar;
  return {
    algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: {
      colorPrimary: v("--fs-color-primary"),
      colorSuccess: v("--fs-color-accent"),
      colorError: v("--fs-color-danger"),
      colorWarning: v("--fs-color-warning"),
      colorInfo: v("--fs-color-info"),
      borderRadius: cssVarPx("--fs-radius-sm"),
      fontFamily: v("--fs-font-ui"),
      colorBgContainer: v("--fs-bg-surface"),
      colorBgElevated: v("--fs-bg-elevated"),
      colorBgLayout: v("--fs-bg-page"),
      colorText: v("--fs-text-primary"),
      colorTextSecondary: v("--fs-text-secondary"),
      colorTextHeading: v("--fs-text-primary"),
      colorBorder: v("--fs-border"),
      colorBorderSecondary: v("--fs-border"),
      colorFillAlter: v("--fs-bg-muted"),
      colorFillContent: v("--fs-border"),
      colorFillSecondary: v("--fs-border"),
    },
    components: {
      Layout: {
        bodyBg: v("--fs-bg-page"),
        headerBg: v("--fs-bg-surface"),
        siderBg: v("--fs-bg-sidebar"),
      },
      Card: {
        colorBgContainer: v("--fs-bg-surface"),
      },
      Table: {
        colorBgContainer: v("--fs-bg-surface"),
        headerBg: v("--fs-bg-header"),
        headerColor: v("--fs-text-primary"),
        rowHoverBg: v("--fs-bg-surface"),
        rowSelectedBg: v("--fs-bg-selected"),
        rowSelectedHoverBg: v("--fs-bg-selected-hover"),
        headerSortActiveBg: v("--fs-bg-header"),
        headerSortHoverBg: v("--fs-bg-header"),
        borderColor: v("--fs-border"),
        footerBg: v("--fs-bg-header"),
        footerColor: v("--fs-text-primary"),
        colorTextHeading: v("--fs-text-primary"),
      },
      Modal: {
        contentBg: v("--fs-bg-modal"),
        headerBg: v("--fs-bg-modal"),
      },
      Drawer: {
        colorBgElevated: v("--fs-bg-modal"),
      },
      Segmented: {
        trackBg: v("--fs-segmented-bg"),
      },
      Menu: {
        darkItemBg: v("--fs-bg-sidebar"),
        darkSubMenuItemBg: v("--fs-bg-sidebar"),
        darkItemColor: v("--fs-sidebar-text"),
        darkItemHoverColor: v("--fs-sidebar-text-active"),
        darkItemHoverBg: v("--fs-bg-sidebar-hover"),
        darkItemSelectedBg: v("--fs-color-primary"),
        darkItemSelectedColor: v("--fs-sidebar-text-active"),
        darkGroupTitleColor: v("--fs-sidebar-text-muted"),
      },
    },
  };
}
