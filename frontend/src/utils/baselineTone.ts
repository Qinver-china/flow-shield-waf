/** deviation_ratio = current / baseline（1 = 与基线持平）。 */
export type BaselineTone = "normal" | "warn" | "danger";

/**
 * 相对基线着色：
 * - ≤ 基线：normal
 * - 高于基线且未满 +100%（ratio < 2）：warn
 * - 高于基线 ≥ +100%（ratio ≥ 2）：danger
 */
export function baselineTone(
  deviationRatio: number | null | undefined,
  warmup?: boolean | null,
): BaselineTone {
  if (warmup || deviationRatio == null || !(deviationRatio > 1)) return "normal";
  if (deviationRatio < 2) return "warn";
  return "danger";
}
