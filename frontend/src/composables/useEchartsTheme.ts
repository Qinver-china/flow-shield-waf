import { storeToRefs } from "pinia";
import { watch } from "vue";
import type { ECharts } from "echarts";
import { useThemeStore } from "@/stores/theme";

export function useEchartsTheme(charts: () => ECharts[]) {
  const theme = useThemeStore();
  const { isDark } = storeToRefs(theme);

  watch(isDark, () => {
    charts().forEach((chart) => {
      const dom = chart.getDom();
      const option = chart.getOption();
      chart.dispose();
      const next = (window as any).echarts?.init(dom, isDark.value ? "dark" : undefined);
      if (next && option) next.setOption(option, true);
    });
  });
}

export function echartsThemeName(isDark: boolean) {
  return isDark ? "dark" : undefined;
}
