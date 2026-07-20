import { computed, type ComputedRef } from "vue";
import { useBreakpoint } from "@/composables/useBreakpoint";

type PaginationSize = "default" | "small";

/**
 * 表格分页尺寸：PC 普通尺寸（带边框），移动端小尺寸。
 * 无边框样式由 global.css 在移动端统一覆盖。
 */
export function useResponsivePagination() {
  const { isMobile } = useBreakpoint();
  const paginationSize: ComputedRef<PaginationSize> = computed(() =>
    isMobile.value ? "small" : "default",
  );

  function withPaginationSize(pagination: false | null | undefined): false | null | undefined;
  function withPaginationSize<T extends Record<string, unknown>>(
    pagination: T,
  ): T & { size: PaginationSize };
  function withPaginationSize<T extends Record<string, unknown>>(
    pagination: T | false | null | undefined,
  ): (T & { size: PaginationSize }) | false | null | undefined {
    if (!pagination || pagination === false) return pagination;
    return { ...pagination, size: paginationSize.value };
  }

  return { isMobile, paginationSize, withPaginationSize };
}
