<template>
  <a-tooltip :title="tooltip">
    <a-button
      type="text"
      class="fs-header-icon-btn theme-toggle"
      :aria-label="tooltip"
      @click="theme.toggle()"
    >
      <sun-outlined v-if="isDark" class="theme-toggle__icon theme-toggle__icon--day" />
      <moon-outlined v-else class="theme-toggle__icon theme-toggle__icon--night" />
    </a-button>
  </a-tooltip>
</template>

<script setup lang="ts">
import AntdIcon from "@ant-design/icons-vue/es/components/AntdIcon";
import SunOutlinedSvg from "@ant-design/icons-svg/es/asn/SunOutlined";
import MoonOutlinedSvg from "@ant-design/icons-svg/es/asn/MoonOutlined";
import { computed, defineComponent, h } from "vue";
import { storeToRefs } from "pinia";
import { useThemeStore } from "@/stores/theme";

function createOutlinedIcon(name: string, icon: typeof SunOutlinedSvg) {
  return defineComponent({
    name,
    inheritAttrs: false,
    setup(props, { attrs }) {
      return () => h(AntdIcon, { ...props, ...attrs, icon });
    },
  });
}

const SunOutlined = createOutlinedIcon("SunOutlined", SunOutlinedSvg);
const MoonOutlined = createOutlinedIcon("MoonOutlined", MoonOutlinedSvg);

const theme = useThemeStore();
const { isDark } = storeToRefs(theme);

const tooltip = computed(() => (isDark.value ? "切换日间模式" : "切换夜间模式"));
</script>

<style scoped>
.theme-toggle__icon {
  font-size: 17px;
  transition: color var(--fs-transition), transform var(--fs-transition);
}

.fs-header-icon-btn:hover .theme-toggle__icon--day {
  color: #f59e0b;
  transform: rotate(-8deg);
}

.fs-header-icon-btn:hover .theme-toggle__icon--night {
  color: var(--fs-color-primary);
  transform: scale(1.08);
}
</style>
