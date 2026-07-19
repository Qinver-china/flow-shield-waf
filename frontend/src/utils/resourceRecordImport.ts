function cloneValue<T>(value: T): T {
  if (value === undefined || value === null) return value;
  return JSON.parse(JSON.stringify(value)) as T;
}

function mergeImportedValue(templateVal: unknown, importedVal: unknown): unknown {
  if (importedVal === undefined) return cloneValue(templateVal);

  if (Array.isArray(templateVal)) {
    return Array.isArray(importedVal) ? cloneValue(importedVal) : cloneValue(templateVal);
  }

  if (templateVal !== null && typeof templateVal === "object") {
    if (importedVal === null || typeof importedVal !== "object" || Array.isArray(importedVal)) {
      return cloneValue(templateVal);
    }
    const result: Record<string, unknown> = {};
    const template = templateVal as Record<string, unknown>;
    const imported = importedVal as Record<string, unknown>;
    for (const key of Object.keys(template)) {
      result[key] = mergeImportedValue(template[key], imported[key]);
    }
    return result;
  }

  return importedVal;
}

export function normalizeImportedRecord(
  parsed: unknown,
  defaultRecord: () => Record<string, unknown>,
  options?: { preserveId?: number | null },
): Record<string, unknown> {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("JSON 必须是对象");
  }

  const template = defaultRecord();
  const source = parsed as Record<string, unknown>;
  const result: Record<string, unknown> = {};

  for (const key of Object.keys(template)) {
    result[key] = mergeImportedValue(template[key], source[key]);
  }

  if (options?.preserveId != null) {
    result.id = options.preserveId;
  }

  return result;
}

export function parseImportedRecordJson(text: string): unknown {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("请输入 JSON 数据");
  }
  try {
    return JSON.parse(trimmed);
  } catch {
    throw new Error("JSON 格式无效");
  }
}
