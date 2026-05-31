"use client";

import type { WeatherHistoryParams } from "@/lib/api";

type Interval = WeatherHistoryParams["interval"];

const OPTIONS: { label: string; value: Interval }[] = [
  { label: "mentah", value: "raw" },
  { label: "1m", value: "1m" },
  { label: "5m", value: "5m" },
  { label: "15m", value: "15m" },
  { label: "1h", value: "1h" },
];

interface IntervalSelectorProps {
  value: Interval;
  onChange: (interval: Interval) => void;
}

export function IntervalSelector({ value, onChange }: IntervalSelectorProps) {
  return (
    <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-0.5">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
            value === opt.value
              ? "bg-blue-600 text-white"
              : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
