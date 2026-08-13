"use client";

import type { WeatherHistoryParams } from "@/lib/api";

type Interval = WeatherHistoryParams["interval"];

const OPTIONS: { label: string; value: Interval }[] = [
  { label: "Data asli", value: "raw" },
  { label: "1 menit", value: "1m" },
  { label: "5 menit", value: "5m" },
  { label: "15 menit", value: "15m" },
  { label: "1 jam", value: "1h" },
];

interface IntervalSelectorProps {
  value: Interval;
  onChange: (interval: Interval) => void;
  disableRaw?: boolean;
}

export function IntervalSelector({ value, onChange, disableRaw = false }: IntervalSelectorProps) {
  return (
    <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-0.5">
      {OPTIONS.map((opt) => {
        const disabled = disableRaw && opt.value === "raw";
        return (
          <button
            key={opt.value}
            type="button"
            disabled={disabled}
            onClick={() => onChange(opt.value)}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              value === opt.value
                ? "bg-blue-600 text-white"
                : disabled
                  ? "cursor-not-allowed text-[var(--color-text-muted)] opacity-40"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            }`}
            title={disabled ? "Data asli hanya tersedia sampai 7 hari" : undefined}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
