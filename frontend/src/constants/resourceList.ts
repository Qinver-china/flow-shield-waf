export const enabledFilterOptions = [
  { label: "已启用", value: true },
  { label: "已停用", value: false },
];

export const modeFilterOptions = [
  { label: "观察", value: "observe" },
  { label: "拦截", value: "block" },
  { label: "数学计算验证", value: "captcha" },
  { label: "JS 挑战", value: "js_challenge" },
  { label: "滑动验证", value: "slide_captcha" },
];

export const exceptionScopeFilterOptions = [
  { label: "全部防护", value: "all" },
  { label: "仅规则", value: "rules" },
  { label: "仅限速", value: "ratelimit" },
];

export const certificateExpiryFilterOptions = [
  { label: "已过期", value: "expired" },
  { label: "30 天内到期", value: "soon" },
  { label: "有效", value: "valid" },
];
