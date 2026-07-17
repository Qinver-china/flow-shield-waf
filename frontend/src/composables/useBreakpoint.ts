import { computed, onMounted, onUnmounted, ref } from "vue";

const MOBILE_MAX = 767;
const TABLET_MAX = 1023;

function readWidth() {
  return typeof window !== "undefined" ? window.innerWidth : 1440;
}

export function useBreakpoint() {
  const width = ref(readWidth());

  function update() {
    width.value = readWidth();
  }

  onMounted(() => {
    window.addEventListener("resize", update);
  });

  onUnmounted(() => {
    window.removeEventListener("resize", update);
  });

  const isMobile = computed(() => width.value <= MOBILE_MAX);
  const isTablet = computed(() => width.value > MOBILE_MAX && width.value <= TABLET_MAX);
  const isDesktop = computed(() => width.value > TABLET_MAX);

  return { width, isMobile, isTablet, isDesktop };
}
