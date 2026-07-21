import * as echarts from "echarts";
import { storeToRefs } from "pinia";
import { watch } from "vue";
import type { ECharts } from "echarts";
import { useThemeStore } from "@/stores/theme";

/** Built-in dark theme uses #100C2A fill; we keep the palette but drop the canvas fill. */
const FS_DARK_THEME = "fs-dark";

let themesRegistered = false;

function ensureEchartsThemes() {
  if (themesRegistered) return;
  themesRegistered = true;

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
    tooltip: {
      axisPointer: {
        lineStyle: { color: "#817f91" },
        crossStyle: { color: "#817f91" },
      },
    },
  });
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
        next.setOption(
          { ...option, backgroundColor: "transparent" } as echarts.EChartsOption,
          true,
        );
      }
    });
  });
}

export function echartsThemeName(isDark: boolean) {
  ensureEchartsThemes();
  return isDark ? FS_DARK_THEME : undefined;
}

/** Always clear canvas fill so charts sit on the page surface. */
export function withTransparentChartBg(
  option: echarts.EChartsOption,
): echarts.EChartsOption {
  return { ...option, backgroundColor: "transparent" };
}
