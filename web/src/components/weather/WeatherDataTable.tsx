"use client";

import { useState, useCallback } from "react";
import type { HistoryPoint } from "@/lib/types";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

const COLUMNS = [
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

type ColKey = (typeof COLUMNS)[number]["key"];

function fmt(val: unknown): string {
  if (val == null) return "—";
  if (typeof val === "number") return val.toFixed(2);
  if (typeof val === "string" && val.includes("T")) {
    return new Date(val).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  return String(val);
}

function exportCsv(series: HistoryPoint[]) {
  const header = COLUMNS.map((c) => c.label).join(",");
  const rows = series.map((p) =>
    COLUMNS.map((c) => {
      const v = p[c.key as keyof HistoryPoint];
      if (v == null) return "";
      if (typeof v === "string" && v.includes(",")) return `"${v}"`;
      return String(v);
    }).join(","),
  );
  const csv = [header, ...rows].join("\n");
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
}

export function WeatherDataTable({ series, loading }: WeatherDataTableProps) {
  const [sortKey, setSortKey] = useState<ColKey>("bucket");
  const [sortAsc, setSortAsc] = useState(false);

  const handleSort = useCallback(
    (key: ColKey) => {
      if (key === sortKey) {
        setSortAsc((v) => !v);
      } else {
        setSortKey(key);
        setSortAsc(false);
      }
    },
    [sortKey],
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
          Data Riwayat
        </p>
        <EmptyState message="Tidak ada data di rentang ini" detail="Sesuaikan rentang waktu atau tunggu sinkronisasi." />
      </Card>
    );
  }

  const sorted = [...series].sort((a, b) => {
    const av = a[sortKey as keyof HistoryPoint];
    const bv = b[sortKey as keyof HistoryPoint];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortAsc ? cmp : -cmp;
  });

  return (
    <Card className="overflow-hidden">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Data Riwayat
          <span className="ml-2 font-normal normal-case">({series.length} baris)</span>
        </p>
        <button
          type="button"
          onClick={() => exportCsv(series)}
          className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-xs font-medium text-[var(--color-text)] transition-colors hover:border-blue-500 hover:text-blue-400"
        >
          Ekspor CSV
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-max text-xs">
          <thead>
            <tr className="border-b border-[var(--color-border)]">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className="cursor-pointer whitespace-nowrap px-3 py-2 text-left font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                  onClick={() => handleSort(col.key)}
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span className="ml-1">{sortAsc ? "↑" : "↓"}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr
                key={i}
                className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-border)] hover:bg-opacity-30"
              >
                {COLUMNS.map((col) => (
                  <td
                    key={col.key}
                    className="whitespace-nowrap px-3 py-2 text-[var(--color-text)]"
                  >
                    {fmt(row[col.key as keyof HistoryPoint])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
