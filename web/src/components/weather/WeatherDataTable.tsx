"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { HistoryPoint } from "@/lib/types";
import { formatWindDirection } from "@/lib/wind";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";
import { useSiteConfig } from "@/components/common/SiteConfigProvider";
import { rainSeriesLabel } from "@/lib/rainSemantics";

const SUMMARY_COLUMNS = [
  { key: "bucket", label: "Waktu" },
  { key: "temperature_avg", label: "Suhu Rata² (°C)" },
  { key: "temperature_min", label: "Suhu Min (°C)" },
  { key: "temperature_max", label: "Suhu Maks (°C)" },
  { key: "humidity_avg", label: "Kelembapan (%)" },
  { key: "pressure_avg", label: "Tekanan (hPa)" },
  { key: "illuminance_avg", label: "Cahaya (lx)" },
  { key: "rain_max", label: "Hujan Maks (mm)" },
  { key: "wind_speed_avg", label: "Angin Rata² (m/s)" },
  { key: "wind_speed_max", label: "Angin Maks (m/s)" },
  { key: "latest_wind_dir_deg", label: "Arah Angin (°)" },
] as const;

const RAW_COLUMNS = [
  { key: "bucket", label: "Waktu" },
  { key: "temperature_c", label: "Suhu (°C)" },
  { key: "humidity_pct", label: "Kelembapan (%)" },
  { key: "pressure_hpa", label: "Tekanan (hPa)" },
  { key: "illuminance_lux", label: "Cahaya (lx)" },
  { key: "rain_mm", label: "Hujan (mm)" },
  { key: "wind_speed_ms", label: "Kecepatan Angin (m/s)" },
  { key: "wind_dir_deg", label: "Arah Angin (°)" },
  { key: "source", label: "Sumber Data" },
  { key: "device", label: "Perangkat Sensor" },
] as const;

type TableRow = HistoryPoint & Record<string, unknown>;
type Column = (typeof SUMMARY_COLUMNS)[number] | (typeof RAW_COLUMNS)[number];
type SortKey = string;

const ROWS_PER_PAGE = 100;

const ONE_DECIMAL_KEYS = new Set([
  "temperature_avg",
  "temperature_min",
  "temperature_max",
  "temperature_c",
  "humidity_avg",
  "humidity_pct",
  "pressure_avg",
  "pressure_hpa",
  "rain_max",
  "rain_mm",
]);

const TWO_DECIMAL_KEYS = new Set([
  "wind_speed_avg",
  "wind_speed_max",
  "wind_speed_ms",
]);

function formatTimestamp(val: string): string {
  return new Date(val).toLocaleString("id-ID", {
    timeZone: "Asia/Jakarta",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatSource(val: string): string {
  if (val === "uno_weather") return "Sensor cuaca";
  return val.replaceAll("_", " ");
}

function formatDevice(val: string): string {
  if (val.includes("DFRobot")) return "USB DFRobot";
  if (val.includes("/dev/serial/by-id/")) {
    return val.split("/dev/serial/by-id/")[1] ?? "Serial USB";
  }
  return val;
}

function hasMeasuredWind(row?: TableRow): boolean {
  if (!row) return false;
  const avg = Number(row.wind_speed_avg ?? row.wind_speed_ms ?? 0);
  const max = Number(row.wind_speed_max ?? row.wind_speed_ms ?? 0);
  return avg !== 0 || max !== 0;
}

function fmt(val: unknown, key?: string, row?: TableRow): string {
  if ((key === "latest_wind_dir_deg" || key === "wind_dir_deg") && !hasMeasuredWind(row)) {
    return "—";
  }
  if (val == null) return "—";
  if (key === "latest_wind_dir_deg" || key === "wind_dir_deg") {
    return formatWindDirection(typeof val === "number" ? val : Number(val));
  }
  if (key === "bucket" && typeof val === "string" && val.includes("T")) {
    return formatTimestamp(val);
  }
  if (key === "source" && typeof val === "string") {
    return formatSource(val);
  }
  if (key === "device" && typeof val === "string") {
    return formatDevice(val);
  }
  if (typeof val === "number") {
    if (key && ONE_DECIMAL_KEYS.has(key)) return val.toFixed(1);
    if (key && TWO_DECIMAL_KEYS.has(key)) return val.toFixed(2);
    return Number.isInteger(val) ? String(val) : val.toFixed(2);
  }
  if (typeof val === "string" && val.includes("T")) {
    return formatTimestamp(val);
  }
  return String(val);
}

function csvCell(value: string): string {
  return /[",\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
}

function exportCsv(series: TableRow[], columns: readonly Column[]) {
  const header = columns.map((c) => csvCell(c.label)).join(",");
  const rows = series.map((row) =>
    columns
      .map((column) => csvCell(fmt(row[column.key as keyof TableRow], column.key, row)))
      .join(","),
  );
  // UTF-8 BOM makes Indonesian Excel recognize headers and symbols such as ° correctly.
  const csv = `\ufeff${[header, ...rows].join("\n")}`;
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `weather-history-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

interface WeatherDataTableProps {
  series: HistoryPoint[];
  loading: boolean;
  rawLimited?: boolean;
}

export function WeatherDataTable({ series, loading, rawLimited = false }: WeatherDataTableProps) {
  const { rainSemantics } = useSiteConfig();
  const rows = series as TableRow[];
  const isRawSeries = rows.length > 0 && "temperature_c" in rows[0];
  const baseColumns = (isRawSeries ? RAW_COLUMNS : SUMMARY_COLUMNS) as readonly Column[];
  const columns = baseColumns.map((column) =>
    column.key === "rain_max" || column.key === "rain_mm"
      ? { ...column, label: rainSeriesLabel(rainSemantics, isRawSeries) }
      : column,
  ) as readonly Column[];

  const [sortKey, setSortKey] = useState<SortKey>("bucket");
  const [sortAsc, setSortAsc] = useState(false);
  const [page, setPage] = useState(1);

  useEffect(() => {
    // Reset table controls when the result shape or dataset changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSortKey("bucket");
    setSortAsc(false);
    setPage(1);
  }, [isRawSeries, series.length]);

  const handleSort = useCallback(
    (key: SortKey) => {
      if (key === sortKey) {
        setSortAsc((v) => !v);
      } else {
        setSortKey(key);
        setSortAsc(false);
      }
      setPage(1);
    },
    [sortKey],
  );

  const sorted = useMemo(() => {
    return [...rows].sort((a, b) => {
      const av = a[sortKey as keyof TableRow];
      const bv = b[sortKey as keyof TableRow];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortAsc ? cmp : -cmp;
    });
  }, [rows, sortAsc, sortKey]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / ROWS_PER_PAGE));
  const pageStart = (page - 1) * ROWS_PER_PAGE;
  const pageRows = useMemo(
    () => sorted.slice(pageStart, pageStart + ROWS_PER_PAGE),
    [pageStart, sorted],
  );

  if (loading) {
    return (
      <Card>
        <div className="h-48 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  if (series.length === 0) {
    return (
      <Card>
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Riwayat Cuaca
        </p>
        <EmptyState
          message="Tidak ada data di rentang ini"
          detail="Sesuaikan rentang waktu atau tunggu sinkronisasi."
        />
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            Detail Cuaca
            <span className="ml-2 font-normal normal-case">({series.length} baris)</span>
          </p>
          <p className="text-xs text-[var(--color-text-muted)]">
            Menampilkan {pageStart + 1}-{Math.min(pageStart + ROWS_PER_PAGE, sorted.length)} dari {sorted.length} baris
            {isRawSeries ? " · dipaginasi agar tetap ringan" : ""}
            {rawLimited ? " · dibatasi ke 3000 data terbaru" : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={() => exportCsv(sorted, columns)}
          className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-xs font-medium text-[var(--color-text)] transition-colors hover:border-blue-500 hover:text-blue-400"
        >
          Ekspor CSV
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-max text-xs">
          <thead>
            <tr className="border-b border-[var(--color-border)]">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="cursor-pointer whitespace-nowrap px-3 py-2 text-left font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                  onClick={() => handleSort(col.key)}
                >
                  {col.label}
                  {sortKey === col.key && <span className="ml-1">{sortAsc ? "↑" : "↓"}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, i) => (
              <tr
                key={`${String(row.bucket)}-${i}`}
                className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-border)] hover:bg-opacity-30"
              >
                {columns.map((col) => (
                  <td key={col.key} className="whitespace-nowrap px-3 py-2 text-[var(--color-text)]">
                    {fmt(row[col.key as keyof TableRow], col.key, row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-xs text-[var(--color-text-muted)] sm:grid-cols-[auto_auto_1fr_auto_auto] sm:items-center">
        <button
          type="button"
          aria-label="Ke halaman awal"
          onClick={() => setPage(1)}
          disabled={page <= 1}
          className="col-start-1 row-start-2 min-h-9 rounded-md border border-[var(--color-border)] px-2 py-1.5 disabled:cursor-not-allowed disabled:opacity-40 sm:row-start-1 sm:px-3"
        >
          « Awal
        </button>
        <button
          type="button"
          aria-label="Ke halaman sebelumnya"
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          className="col-start-2 row-start-2 min-h-9 rounded-md border border-[var(--color-border)] px-2 py-1.5 disabled:cursor-not-allowed disabled:opacity-40 sm:row-start-1 sm:px-3"
        >
          <span className="sm:hidden">‹</span>
          <span className="hidden sm:inline">Sebelumnya</span>
        </button>
        <span
          aria-live="polite"
          className="col-span-4 col-start-1 row-start-1 text-center font-medium sm:col-span-1 sm:col-start-3"
        >
          Halaman {page} / {totalPages}
        </span>
        <button
          type="button"
          aria-label="Ke halaman berikutnya"
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages}
          className="col-start-3 row-start-2 min-h-9 rounded-md border border-[var(--color-border)] px-2 py-1.5 disabled:cursor-not-allowed disabled:opacity-40 sm:col-start-4 sm:row-start-1 sm:px-3"
        >
          <span className="sm:hidden">›</span>
          <span className="hidden sm:inline">Berikutnya</span>
        </button>
        <button
          type="button"
          aria-label="Ke halaman akhir"
          onClick={() => setPage(totalPages)}
          disabled={page >= totalPages}
          className="col-start-4 row-start-2 min-h-9 rounded-md border border-[var(--color-border)] px-2 py-1.5 disabled:cursor-not-allowed disabled:opacity-40 sm:col-start-5 sm:row-start-1 sm:px-3"
        >
          Akhir »
        </button>
      </div>
    </Card>
  );
}
