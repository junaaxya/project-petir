"use client";

interface NodeSelectProps {
  value: string;
  onChange: (node: string) => void;
  nodes?: string[];
}

export function NodeSelect({ value, onChange, nodes = [] }: NodeSelectProps) {
  return (
    <div className="flex items-center gap-2">
      <label
        htmlFor="node-select"
        className="text-xs font-medium text-[var(--color-text-muted)]"
      >
        Node
      </label>
      <select
        id="node-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-sm text-[var(--color-text)] focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        <option value="">Semua node</option>
        {nodes.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </div>
  );
}
