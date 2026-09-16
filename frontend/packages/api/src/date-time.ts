const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?$/;

type DateTimeParts = {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
};

export function isValidTimeZone(timeZone: string) {
  try {
    new Intl.DateTimeFormat("en", { timeZone }).format();
    return true;
  } catch {
    return false;
  }
}

export function parseUtcDateTime(value?: string | null) {
  if (!value) return null;
  const normalized = value.trim().replace(" ", "T");
  const withZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(normalized) ? normalized : `${normalized}Z`;
  const parsed = new Date(withZone);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function zonedDateTimeToUtc(value: string, timeZone: string) {
  const wallClock = parseWallClock(value);
  if (!wallClock || !isValidTimeZone(timeZone)) return null;

  const wallClockAsUtc = Date.UTC(
    wallClock.year,
    wallClock.month - 1,
    wallClock.day,
    wallClock.hour,
    wallClock.minute,
    wallClock.second
  );
  let candidate = wallClockAsUtc;

  for (let index = 0; index < 3; index += 1) {
    const displayed = partsInTimeZone(new Date(candidate), timeZone);
    if (!displayed) return null;
    const offset = Date.UTC(
      displayed.year,
      displayed.month - 1,
      displayed.day,
      displayed.hour,
      displayed.minute,
      displayed.second
    ) - candidate;
    const next = wallClockAsUtc - offset;
    if (next === candidate) break;
    candidate = next;
  }

  const resolved = new Date(candidate);
  const displayed = partsInTimeZone(resolved, timeZone);
  return displayed && sameParts(displayed, wallClock) ? resolved : null;
}

export function toUtcApiDateTime(value: string, timeZone: string) {
  const date = zonedDateTimeToUtc(value, timeZone);
  if (!date) return "";
  return [
    `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`,
    `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}`
  ].join(" ");
}

export function utcDateTimeToZonedInput(value: string | undefined, timeZone: string) {
  const date = parseUtcDateTime(value);
  if (!date || !isValidTimeZone(timeZone)) return "";
  const parts = partsInTimeZone(date, timeZone);
  if (!parts) return "";
  return `${parts.year}-${pad(parts.month)}-${pad(parts.day)}T${pad(parts.hour)}:${pad(parts.minute)}`;
}

export function formatUtcDateTimeInZone(
  value: string | undefined,
  timeZone: string,
  options: { includeYear?: boolean } = {}
) {
  const date = parseUtcDateTime(value);
  if (!date || !isValidTimeZone(timeZone)) return value || "-";
  const parts = partsInTimeZone(date, timeZone);
  if (!parts) return value || "-";
  const datePart = options.includeYear === false
    ? `${pad(parts.month)}/${pad(parts.day)}`
    : `${parts.year}-${pad(parts.month)}-${pad(parts.day)}`;
  return `${datePart} ${pad(parts.hour)}:${pad(parts.minute)}`;
}

function parseWallClock(value: string): DateTimeParts | null {
  const match = DATE_TIME_PATTERN.exec(value.trim());
  if (!match) return null;
  const parts = {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
    hour: Number(match[4]),
    minute: Number(match[5]),
    second: Number(match[6] ?? 0)
  };
  const probe = new Date(Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second));
  return probe.getUTCFullYear() === parts.year
    && probe.getUTCMonth() + 1 === parts.month
    && probe.getUTCDate() === parts.day
    && probe.getUTCHours() === parts.hour
    && probe.getUTCMinutes() === parts.minute
    && probe.getUTCSeconds() === parts.second
    ? parts
    : null;
}

function partsInTimeZone(date: Date, timeZone: string): DateTimeParts | null {
  try {
    const values = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hourCycle: "h23"
    }).formatToParts(date).map((part) => [part.type, part.value]));
    return {
      year: Number(values.year),
      month: Number(values.month),
      day: Number(values.day),
      hour: Number(values.hour),
      minute: Number(values.minute),
      second: Number(values.second)
    };
  } catch {
    return null;
  }
}

function sameParts(left: DateTimeParts, right: DateTimeParts) {
  return left.year === right.year
    && left.month === right.month
    && left.day === right.day
    && left.hour === right.hour
    && left.minute === right.minute
    && left.second === right.second;
}

function pad(value: number) {
  return String(value).padStart(2, "0");
}
