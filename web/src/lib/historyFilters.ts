export type HistoryRangePreset = "1d" | "7d" | "30d" | "365d" | "custom";

export const HISTORY_RANGE_OPTIONS: { label: string; value: HistoryRangePreset }[] = [
  { label: "1 hari", value: "1d" },
  { label: "1 minggu", value: "7d" },
  { label: "1 bulan", value: "30d" },
  { label: "1 tahun", value: "365d" },
  { label: "Custom", value: "custom" },
];

const WIB_OFFSET_MINUTES = 7 * 60;
const WIB_OFFSET_MS = WIB_OFFSET_MINUTES * 60 * 1000;

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function formatYmdFromUtcParts(year: number, month: number, day: number): string {
  return `${year}-${pad(month)}-${pad(day)}`;
}

function toWibShiftedDate(date: Date): Date {
  return new Date(date.getTime() + WIB_OFFSET_MS);
}

function fromWibYmd(dateYmd: string): Date {
  return new Date(`${dateYmd}T00:00:00+07:00`);
}

export function toDateInputValue(date: Date): string {
  const shifted = toWibShiftedDate(date);
  return formatYmdFromUtcParts(
    shifted.getUTCFullYear(),
    shifted.getUTCMonth() + 1,
    shifted.getUTCDate(),
  );
}

export function presetToDateRange(preset: Exclude<HistoryRangePreset, "custom">, now = new Date()): { fromDate: string; toDate: string } {
  const shifted = toWibShiftedDate(now);
  const end = new Date(Date.UTC(shifted.getUTCFullYear(), shifted.getUTCMonth(), shifted.getUTCDate()));
  const start = new Date(end);

  switch (preset) {
    case "1d":
      break;
    case "7d":
      start.setUTCDate(start.getUTCDate() - 6);
      break;
    case "30d":
      start.setUTCDate(start.getUTCDate() - 29);
      break;
    case "365d":
      start.setUTCDate(start.getUTCDate() - 364);
      break;
  }

  return {
    fromDate: formatYmdFromUtcParts(start.getUTCFullYear(), start.getUTCMonth() + 1, start.getUTCDate()),
    toDate: formatYmdFromUtcParts(end.getUTCFullYear(), end.getUTCMonth() + 1, end.getUTCDate()),
  };
}

export function normalizeDateRange(fromDate: string, toDate: string): { fromDate: string; toDate: string } {
  if (!fromDate && !toDate) {
    return presetToDateRange("1d");
  }
  if (!fromDate) {
    return { fromDate: toDate, toDate };
  }
  if (!toDate) {
    return { fromDate, toDate: fromDate };
  }
  return fromDate <= toDate ? { fromDate, toDate } : { fromDate: toDate, toDate: fromDate };
}

export function dateRangeToApiRange(fromDate: string, toDate: string): { from: string; to: string } {
  const normalized = normalizeDateRange(fromDate, toDate);
  return {
    from: `${normalized.fromDate}T00:00:00+07:00`,
    to: `${normalized.toDate}T23:59:59.999+07:00`,
  };
}

export function formatDateRangeSummary(fromDate: string, toDate: string): string {
  const normalized = normalizeDateRange(fromDate, toDate);
  const formatter = new Intl.DateTimeFormat("id-ID", {
    timeZone: "Asia/Jakarta",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  const fromLabel = formatter.format(fromWibYmd(normalized.fromDate));
  const toLabel = formatter.format(fromWibYmd(normalized.toDate));
  return normalized.fromDate === normalized.toDate ? fromLabel : `${fromLabel} – ${toLabel}`;
}

export function parseHistoryRangePreset(value: string | null | undefined): HistoryRangePreset {
  if (value === "1d" || value === "7d" || value === "30d" || value === "365d" || value === "custom") {
    return value;
  }
  return "1d";
}

export function parsePositiveInt(value: string | null | undefined, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 1) return fallback;
  return Math.floor(parsed);
}
