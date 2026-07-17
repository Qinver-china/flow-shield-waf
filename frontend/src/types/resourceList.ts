export interface ResourceFilterField {
  key: string;
  label: string;
  type: "search" | "select" | "site";
  placeholder?: string;
  width?: number | string;
  options?: { label: string; value: string | number | boolean }[];
}

export interface ResourceDefaultSort {
  field: string;
  order: "asc" | "desc";
}

export interface ResourceColumn {
  title: string;
  dataIndex?: string;
  key?: string;
  width?: number;
  ellipsis?: boolean;
  slotCell?: boolean;
  sorter?: boolean;
  sortKey?: string;
  customRender?: (ctx: { text: unknown; record: Record<string, unknown> }) => unknown;
}
