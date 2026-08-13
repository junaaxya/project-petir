"use client";

import type { HistoryRangePreset } from "@/lib/historyFilters";
import { formatDateRangeSummary, HISTORY_RANGE_OPTIONS } from "@/lib/historyFilters";

interface HistoryFilterBarProps {
  preset: HistoryRangePreset;
  fromDate: string;
  toDate: string;
  onPresetChange: (preset: HistoryRangePreset) => void;
  onFromDateChange: (value: string) => void;
  onToDateChange: (value: string) => void;
}

export function HistoryFilterBar({
  preset,
  fromDate,
  toDate,
  onPresetChange,
  onFromDateChange,
  onToDateChange,
}: HistoryFilterBarProps) {
  const summary = formatDateRangeSummary(fromDate, toDate);
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 sm:p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            Filter waktu audit
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-blue-800 bg-blue-900/20 px-2.5 py-1 text-xs font-medium text-blue-300">
              {preset === "custom" ? "Custom" : "Preset cepat"}
            </span>
            <span className="text-sm font-medium text-[var(--color-text)]">{summary}</span>
          </div>
        </div>
        <span className="text-xs text-[var(--color-text-muted)]">Semua tanggal mengikuti WIB</span>
      </div>
      <div className="flex flex-wrap items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-0.5">
        {HISTORY_RANGE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onPresetChange(opt.value)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              preset === opt.value
                ? "bg-blue-600 text-white"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <label className="flex min-w-0 flex-col gap-1.5">
          <span className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            Mulai
          </span>
          <input
            type="date"
            value={fromDate}
            onChange={(event) => onFromDateChange(event.target.value)}
            className="min-w-0 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2.5 text-sm text-[var(--color-text)] outline-none transition-colors focus:border-blue-500"
          />
        </label>
        <label className="flex min-w-0 flex-col gap-1.5">
          <span className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            Sampai
          </span>
          <input
            type="date"
            value={toDate}
            onChange={(event) => onToDateChange(event.target.value)}
            className="min-w-0 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2.5 text-sm text-[var(--color-text)] outline-none transition-colors focus:border-blue-500"
          />
        </label>
      </div>
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]/30 p-3 text-xs text-[var(--color-text-muted)]">
        Pilih rentang tanggal untuk audit riwayat atau log. Untuk melihat satu hari tertentu, isi tanggal mulai dan sampai dengan tanggal yang sama.
      </div>
    </div>
  );
}
