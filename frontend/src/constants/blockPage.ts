export const BLOCK_STATUS_OPTIONS = [
  { value: 403, label: "403 Forbidden" },
  { value: 429, label: "429 Too Many Requests" },
  { value: 451, label: "451 Unavailable For Legal Reasons" },
  { value: 503, label: "503 Service Unavailable" },
];

export const BLOCK_PAGE_FIELD_DEFAULTS = {
  custom_block_page_enabled: false,
  block_page_status_code: 403,
  block_page_html: "",
} as const;

export function validateBlockPageOverride(record: Record<string, unknown>) {
  if (record.custom_block_page_enabled && !(String(record.block_page_html || "").trim())) {
    throw new Error("启用自定义拦截页时必须填写 HTML 内容");
  }
}
