import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";

interface MetricCardProps {
  label: string;
  value: number | null | undefined;
  unit: string;
  min?: number | null;
  max?: number | null;
  loading?: boolean;
  emptyMessage?: string;
  emptyDetail?: string;
}

function fmt(v: number | null | undefined, decimals = 1): string {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

export function MetricCard({ label, value, unit, min, max, loading, emptyMessage, emptyDetail }: MetricCardProps) {
  return (
    <Card className="flex min-h-[118px] flex-col justify-between sm:min-h-[128px]">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
        {label}
      </p>
      {loading ? (
        <div className="mt-2 h-8 w-24 animate-pulse rounded bg-[var(--color-border)]" />
      ) : value == null ? (
        <EmptyState message={emptyMessage ?? "Tidak ada data"} detail={emptyDetail} />
      ) : (
        <>
          <p className="mt-1.5 font-mono text-lg font-semibold text-[var(--color-text)] sm:text-3xl">
            {fmt(value)}
            <span className="ml-1 text-xs font-normal text-[var(--color-text-muted)] sm:text-base">
              {unit}
            </span>
          </p>
          {(min != null || max != null) && (
            <p className="mt-1.5 font-mono text-[11px] text-[var(--color-text-muted)] sm:text-xs">
              {fmt(min)} – {fmt(max)} {unit}
            </p>
          )}
        </>
      )}
    </Card>
  );
}
