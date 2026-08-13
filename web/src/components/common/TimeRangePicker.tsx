"use client";

export type TimeRange = "1d" | "7d" | "30d" | "365d";

const OPTIONS: { label: string; value: TimeRange }[] = [
  { label: "1 hari", value: "1d" },
  { label: "7 hari", value: "7d" },
  { label: "1 bulan", value: "30d" },
  { label: "1 tahun", value: "365d" },
];

interface TimeRangePickerProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

export function TimeRangePicker({ value, onChange }: TimeRangePickerProps) {
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

export function timeRangeToFromTo(range: TimeRange): { from: string; to: string } {
  const to = new Date();
  const from = new Date(to);
  switch (range) {
    case "1d":
      from.setDate(from.getDate() - 1);
      break;
    case "7d":
      from.setDate(from.getDate() - 7);
      break;
    case "30d":
      from.setMonth(from.getMonth() - 1);
      break;
    case "365d":
      from.setFullYear(from.getFullYear() - 1);
      break;
  }
  return { from: from.toISOString(), to: to.toISOString() };
}
