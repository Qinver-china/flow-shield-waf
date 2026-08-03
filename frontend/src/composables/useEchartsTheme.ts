import * as echarts from "echarts";
import { storeToRefs } from "pinia";
import { watch } from "vue";
import type { ECharts, EChartsOption, TooltipComponentOption } from "echarts";
import { useThemeStore } from "@/stores/theme";

const FS_LIGHT_THEME = "fs-light";
/** Built-in dark theme uses #100C2A fill; we keep the palette but drop the canvas fill. */
const FS_DARK_THEME = "fs-dark";

let themesRegistered = false;

const CHART_TOOLTIP_LIGHT: TooltipComponentOption = {
  backgroundColor: "#ffffff",
  borderColor: "#e2e8f0",
  borderWidth: 1,
  textStyle: { color: "#0f172a", fontSize: 12 },
  axisPointer: {
    lineStyle: { color: "#94a3b8" },
    crossStyle: { color: "#94a3b8" },
  },
};

const CHART_TOOLTIP_DARK: TooltipComponentOption = {
  backgroundColor: "#1e293b",
  borderColor: "#334155",
  borderWidth: 1,
  textStyle: { color: "#f8fafc", fontSize: 12 },
  axisPointer: {
    lineStyle: { color: "#64748b" },
    crossStyle: { color: "#64748b" },
  },
};

export function chartTooltipDefaults(isDark: boolean): TooltipComponentOption {
  return isDark ? CHART_TOOLTIP_DARK : CHART_TOOLTIP_LIGHT;
}

function ensureEchartsThemes() {
  if (themesRegistered) return;
  themesRegistered = true;

  echarts.registerTheme(FS_LIGHT_THEME, {
    backgroundColor: "transparent",
    tooltip: CHART_TOOLTIP_LIGHT,
  });

  const contrastColor = "#B9B8CE";
  const axisCommon = () => ({
    axisLine: { lineStyle: { color: contrastColor } },
    axisTick: { lineStyle: { color: contrastColor } },
    axisLabel: { color: contrastColor },
    splitLine: { lineStyle: { color: "#484753" } },
    splitArea: {
      areaStyle: {
        color: ["rgba(255,255,255,0.02)", "rgba(255,255,255,0.05)"],
      },
    },
  });

  echarts.registerTheme(FS_DARK_THEME, {
    darkMode: true,
    color: [
      "#4992ff",
      "#7cffb2",
      "#fddd60",
      "#ff6e76",
      "#58d9f9",
      "#05c091",
      "#ff8a45",
      "#8d48e3",
      "#dd79ff",
    ],
    backgroundColor: "transparent",
    textStyle: { color: contrastColor },
    title: {
      textStyle: { color: "#EEEEEE" },
      subtextStyle: { color: "#AAAAAA" },
    },
    line: {
      itemStyle: { borderWidth: 1 },
      lineStyle: { width: 2 },
      symbolSize: 4,
      symbol: "circle",
      smooth: false,
    },
    radar: {
      itemStyle: { borderWidth: 1 },
      lineStyle: { width: 2 },
      symbolSize: 4,
      symbol: "circle",
      smooth: false,
    },
    bar: {
      itemStyle: { barBorderWidth: 0, barBorderColor: "#ccc" },
    },
    pie: {
      itemStyle: { borderWidth: 0, borderColor: "#ccc" },
    },
    categoryAxis: {
      ...axisCommon(),
      splitLine: { show: false, lineStyle: { color: "#484753" } },
    },
    valueAxis: axisCommon(),
    logAxis: axisCommon(),
    timeAxis: axisCommon(),
    legend: {
      textStyle: { color: contrastColor },
    },
    tooltip: CHART_TOOLTIP_DARK,
  });
}

export function mergeChartTooltip(option: EChartsOption, isDark: boolean): EChartsOption {
  if (option.tooltip === false) return option;

  const defaults = chartTooltipDefaults(isDark);
  const userTooltip =
    option.tooltip === true || option.tooltip == null ? {} : option.tooltip;

  return {
    ...option,
    tooltip: {
      ...defaults,
      ...userTooltip,
      textStyle: {
        ...defaults.textStyle,
        ...(userTooltip.textStyle ?? {}),
      },
      axisPointer: {
        ...defaults.axisPointer,
        ...(userTooltip.axisPointer ?? {}),
      },
    },
  };
}

export function useEchartsTheme(charts: () => ECharts[]) {
  const theme = useThemeStore();
  const { isDark } = storeToRefs(theme);

  watch(isDark, () => {
    ensureEchartsThemes();
    charts().forEach((chart) => {
      const dom = chart.getDom();
      const option = chart.getOption();
      chart.dispose();
      const next = echarts.init(dom, echartsThemeName(isDark.value));
      if (option) {
        next.setOption(prepareChartOption(option as EChartsOption, isDark.value), true);
      }
    });
  });
}

export function echartsThemeName(isDark: boolean) {
  ensureEchartsThemes();
  return isDark ? FS_DARK_THEME : FS_LIGHT_THEME;
}

/** Merge tooltip colors + clear canvas fill so charts sit on the page surface. */
export function prepareChartOption(option: EChartsOption, isDark: boolean): EChartsOption {
  return withTransparentChartBg(mergeChartTooltip(option, isDark));
}

/** Always clear canvas fill so charts sit on the page surface. */
export function withTransparentChartBg(option: EChartsOption): EChartsOption {
  return { ...option, backgroundColor: "transparent" };
}
