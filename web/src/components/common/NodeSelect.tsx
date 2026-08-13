"use client";

interface NodeSelectProps {
  value: string;
  onChange: (node: string) => void;
  nodes?: string[];
}

export function NodeSelect({ value, onChange, nodes = [] }: NodeSelectProps) {
  if (nodes.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
          Cakupan data
        </p>
        <p className="text-sm font-medium text-[var(--color-text)]">Semua lokasi sensor</p>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2">
      <label htmlFor="node-select" className="text-xs font-medium text-[var(--color-text-muted)]">
        Lokasi sensor
      </label>
      <select
        id="node-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-2 py-1 text-sm text-[var(--color-text)] focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        <option value="">Semua lokasi</option>
        {nodes.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </div>
  );
}
