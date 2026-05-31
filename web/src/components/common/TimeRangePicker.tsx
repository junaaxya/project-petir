"use client";

export type TimeRange = "1h" | "6h" | "24h" | "7d";

const OPTIONS: { label: string; value: TimeRange }[] = [
  { label: "1h", value: "1h" },
  { label: "6h", value: "6h" },
  { label: "24h", value: "24h" },
  { label: "7d", value: "7d" },
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
    case "1h":
      from.setHours(from.getHours() - 1);
      break;
    case "6h":
      from.setHours(from.getHours() - 6);
      break;
    case "24h":
      from.setHours(from.getHours() - 24);
      break;
    case "7d":
      from.setDate(from.getDate() - 7);
      break;
  }
  return { from: from.toISOString(), to: to.toISOString() };
}
