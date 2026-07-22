/** deviation_ratio = current / baseline（1 = 与基线持平）。 */
export type BaselineTone = "normal" | "warn" | "danger";

/**
 * 相对基线着色（学习中同样按比值着色，不因 warmup 压制）：
 * - ≤ 基线 +20%（ratio ≤ 1.2）：normal
 * - 超过基线 20% 且未满 +100%（1.2 < ratio < 2）：warn（黄）
 * - 超过基线 ≥ +100%（ratio ≥ 2）：danger（红）
 *
 * ``warmup`` 仅保留兼容参数，不再影响着色。
 */
export function baselineTone(
  deviationRatio: number | null | undefined,
  _warmup?: boolean | null,
): BaselineTone {
  if (deviationRatio == null || !(deviationRatio > 1.2)) return "normal";
  if (deviationRatio < 2) return "warn";
  return "danger";
}
