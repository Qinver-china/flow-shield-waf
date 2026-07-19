/** Count leaf conditions in a unified condition tree (supports bare leaf root). */
export function countLeafConditions(node: unknown): number {
  if (!node || typeof node !== "object") return 0;
  const record = node as Record<string, unknown>;
  if (typeof record.field === "string" && record.field) return 1;
  if (Array.isArray(record.conditions)) {
    return record.conditions.reduce<number>(
      (sum, child) => sum + countLeafConditions(child),
      0,
    );
  }
  return 0;
}

/** True when the tree contains at least one leaf condition. */
export function hasMatchingConditions(conditions: unknown): boolean {
  return countLeafConditions(conditions) > 0;
}
