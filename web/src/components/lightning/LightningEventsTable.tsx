"use client";

import { useState } from "react";
import type { LightningEvent } from "@/lib/api";
import type { LightningEventType } from "@contracts";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";
import { InfoTooltip } from "@/components/common/InfoTooltip";

function fmtTs(ts: string): string {
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

const EVENT_TYPE_LABELS: Record<LightningEventType, string> = {
  lightning: "Petir",
  disturber: "Gangguan",
  noise: "Derau",
};

const EVENT_TYPE_COLORS: Record<LightningEventType, string> = {
  lightning: "text-amber-400",
  disturber: "text-indigo-400",
  noise: "text-slate-400",
};

const FILTER_OPTIONS: { label: string; value: LightningEventType | "all" }[] = [
  { label: "Semua", value: "all" },
  { label: "Petir", value: "lightning" },
  { label: "Gangguan", value: "disturber" },
  { label: "Derau", value: "noise" },
];

const CSV_COLUMNS: { key: keyof LightningEvent; label: string }[] = [
  { key: "ts_pi_utc", label: "Waktu" },
  { key: "event_type", label: "Tipe" },
  { key: "distance_km", label: "Jarak (km)" },
  { key: "energy_raw", label: "Energi" },
  { key: "noise_level", label: "Tingkat Derau" },
];

function exportCsv(events: LightningEvent[]) {
  const header = CSV_COLUMNS.map((c) => c.label).join(",");
  const rows = events.map((e) =>
    CSV_COLUMNS.map((c) => {
      const v = e[c.key];
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
  a.download = `lightning-events-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

interface LightningEventsTableProps {
  items: LightningEvent[];
  loading: boolean;
}

export function LightningEventsTable({ items, loading }: LightningEventsTableProps) {
  const [filter, setFilter] = useState<LightningEventType | "all">("all");

  const filtered =
    filter === "all" ? items : items.filter((e) => e.event_type === filter);

  if (loading) {
    return (
      <Card>
        <div className="h-48 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Kejadian Terbaru
          <span className="ml-2 font-normal normal-case">({filtered.length} baris)</span>
        </p>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-0.5">
            {FILTER_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setFilter(opt.value)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  filter === opt.value
                    ? "bg-blue-600 text-white"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => exportCsv(filtered)}
            disabled={filtered.length === 0}
            className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-xs font-medium text-[var(--color-text)] transition-colors hover:border-blue-500 hover:text-blue-400 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-[var(--color-border)] disabled:hover:text-[var(--color-text)]"
          >
            Ekspor CSV
          </button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState message="Tidak ada kejadian" detail="Tidak ada kejadian yang cocok dengan filter saat ini." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="pb-2 text-left text-xs font-medium text-[var(--color-text-muted)]">
                  Waktu
                </th>
                <th className="pb-2 text-left text-xs font-medium text-[var(--color-text-muted)]">
                  <span className="inline-flex items-center gap-1">
                    Tipe
                    <InfoTooltip
                      text="Petir = sambaran asli · Gangguan = interferensi buatan manusia · Derau = derau latar tinggi"
                      label="Keterangan tipe kejadian"
                    />
                  </span>
                </th>
                <th className="pb-2 text-right text-xs font-medium text-[var(--color-text-muted)]">
                  Jarak (km)
                </th>
                <th className="pb-2 text-right text-xs font-medium text-[var(--color-text-muted)]">
                  Energi
                </th>
                <th className="pb-2 text-right text-xs font-medium text-[var(--color-text-muted)]">
                  Tingkat Derau
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((event) => {
                const typeColor =
                  event.event_type ? EVENT_TYPE_COLORS[event.event_type] : "text-[var(--color-text-muted)]";
                const typeLabel =
                  event.event_type ? EVENT_TYPE_LABELS[event.event_type] : "—";
                return (
                  <tr
                    key={event.edge_id}
                    className="border-b border-[var(--color-border)] last:border-0"
                  >
                    <td className="py-2 text-[var(--color-text)]">{fmtTs(event.ts_pi_utc)}</td>
                    <td className={`py-2 font-medium ${typeColor}`}>{typeLabel}</td>
                    <td className="py-2 text-right text-[var(--color-text)]">
                      {event.distance_km != null ? event.distance_km : "—"}
                    </td>
                    <td className="py-2 text-right text-[var(--color-text)]">
                      {event.energy_raw != null ? event.energy_raw : "—"}
                    </td>
                    <td className="py-2 text-right text-[var(--color-text)]">
                      {event.noise_level != null ? event.noise_level : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
