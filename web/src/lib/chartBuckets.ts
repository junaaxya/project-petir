import type { HistoryPoint } from "@/lib/types";

const CHART_TIME_FORMATTER = new Intl.DateTimeFormat("id-ID", {
  timeZone: "Asia/Jakarta",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const COVERAGE_DATE_FORMATTER = new Intl.DateTimeFormat("id-ID", {
  timeZone: "Asia/Jakarta",
  day: "2-digit",
  month: "short",
  year: "numeric",
});

/** Build shared axis labels once per history response instead of once per chart. */
export function formatChartBuckets(series: HistoryPoint[]): string[] {
  return series.map((point) => CHART_TIME_FORMATTER.format(new Date(point.bucket as string)));
}

/** Describe the timestamps actually present without implying missing dates contain data. */
export function formatDataCoverage(series: HistoryPoint[]): string | null {
  if (series.length === 0) return null;
  const first = new Date(series[0].bucket as string);
  const last = new Date(series[series.length - 1].bucket as string);
  return `${COVERAGE_DATE_FORMATTER.format(first)} – ${COVERAGE_DATE_FORMATTER.format(last)}`;
}
