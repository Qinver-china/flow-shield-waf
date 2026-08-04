import { computed, type ComputedRef } from "vue";
import { useBreakpoint } from "@/composables/useBreakpoint";

export const DEFAULT_PAGE_SIZE = 20;
export const DEFAULT_PAGE_SIZE_OPTIONS = ["20", "50", "100"];

type PaginationSize = "default" | "small";

export type TablePaginationConfig = {
  current?: number;
  pageSize?: number;
  total?: number;
  showSizeChanger?: boolean;
  pageSizeOptions?: string[];
  showTotal?: (total: number) => string;
  size?: PaginationSize;
  [key: string]: unknown;
};

/**
 * 表格分页尺寸：PC 普通尺寸（带边框），移动端小尺寸。
 * 无边框样式由 global.css 在移动端统一覆盖。
 * 当 total > DEFAULT_PAGE_SIZE 时显示每页条数选择器。
 */
export function useResponsivePagination() {
  const { isMobile } = useBreakpoint();
  const paginationSize: ComputedRef<PaginationSize> = computed(() =>
    isMobile.value ? "small" : "default",
  );

  function withPaginationSize(pagination: false | null | undefined): false | null | undefined;
  function withPaginationSize<T extends TablePaginationConfig>(
    pagination: T,
  ): T & { size: PaginationSize; showSizeChanger: boolean; pageSizeOptions: string[] };
  function withPaginationSize<T extends TablePaginationConfig>(
    pagination: T | false | null | undefined,
  ): (T & { size: PaginationSize; showSizeChanger: boolean; pageSizeOptions: string[] }) | false | null | undefined {
    if (!pagination || pagination === false) return pagination;
    const total = Number(pagination.total ?? 0);
    return {
      ...pagination,
      size: paginationSize.value,
      pageSizeOptions: pagination.pageSizeOptions ?? DEFAULT_PAGE_SIZE_OPTIONS,
      showSizeChanger: total > DEFAULT_PAGE_SIZE,
    };
  }

  return { isMobile, paginationSize, withPaginationSize, DEFAULT_PAGE_SIZE, DEFAULT_PAGE_SIZE_OPTIONS };
}
