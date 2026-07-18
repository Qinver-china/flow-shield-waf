import dayjs, { type ConfigType, type Dayjs } from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

dayjs.extend(utc);
dayjs.extend(timezone);

export const DEFAULT_TIMEZONE = "Asia/Shanghai";

let appTimezone = DEFAULT_TIMEZONE;

export function setAppTimezone(tz: string) {
  appTimezone = tz || DEFAULT_TIMEZONE;
}

export function getAppTimezone() {
  return appTimezone;
}

/** Backend datetimes are UTC; naive ISO strings must be treated as UTC. */
export function parseUtc(value: string): Dayjs {
  const trimmed = value.trim();
  const hasOffset = /[zZ]$/.test(trimmed) || /[+-]\d{2}:\d{2}$/.test(trimmed);
  const normalized = trimmed.replace(" ", "T");
  return hasOffset ? dayjs.utc(normalized) : dayjs.utc(`${normalized}Z`);
}

export function nowInAppTz(): Dayjs {
  return dayjs().tz(appTimezone);
}

export function toAppTz(value: ConfigType): Dayjs {
  if (dayjs.isDayjs(value)) {
    return value.tz(appTimezone, true);
  }
  return parseUtc(String(value)).tz(appTimezone);
}

export function formatDateTime(
  value?: string | null,
  format = "YYYY-MM-DD HH:mm:ss",
): string {
  if (!value) return "-";
  try {
    return parseUtc(value).tz(appTimezone).format(format);
  } catch {
    return String(value);
  }
}

export function formatDateTimeShort(value?: string | null): string {
  return formatDateTime(value, "MM-DD HH:mm");
}

/** Rolling window label in app timezone, e.g. `2026-07-17 15:00 ~ 2026-07-18 15:00`. */
export function formatWindowRange(hours: number, end?: ConfigType | number): string {
  const endTz = end == null
    ? nowInAppTz()
    : typeof end === "number"
      ? dayjs(end).tz(appTimezone)
      : toAppTz(end);
  const startTz = endTz.subtract(hours, "hour");
  const fmt = "YYYY-MM-DD HH:mm:ss";
  return `${startTz.format(fmt)} ~ ${endTz.format(fmt)}`;
}

export function toUtcIso(value: Dayjs): string {
  return value.tz(appTimezone, true).utc().toISOString();
}
