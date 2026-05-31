import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";

interface MetricCardProps {
  label: string;
  value: number | null | undefined;
  unit: string;
  min?: number | null;
  max?: number | null;
  loading?: boolean;
}

function fmt(v: number | null | undefined, decimals = 1): string {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

export function MetricCard({ label, value, unit, min, max, loading }: MetricCardProps) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        {label}
      </p>
      {loading ? (
        <div className="mt-2 h-8 w-24 animate-pulse rounded bg-[var(--color-border)]" />
      ) : value == null ? (
        <EmptyState message="Tidak ada data" />
      ) : (
        <>
          <p className="mt-1 font-mono text-xl sm:text-3xl font-semibold text-[var(--color-text)]">
            {fmt(value)}
            <span className="ml-1 text-sm sm:text-base font-normal text-[var(--color-text-muted)]">
              {unit}
            </span>
          </p>
          {(min != null || max != null) && (
            <p className="mt-1 font-mono text-xs text-[var(--color-text-muted)]">
              {fmt(min)} – {fmt(max)} {unit}
            </p>
          )}
        </>
      )}
    </Card>
  );
}
