import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";
import { windCompassLabel, windCompassShort } from "@/lib/wind";

interface WindDirectionCardProps {
  deg: number | null | undefined;
  windSpeed: number | null | undefined;
  loading?: boolean;
}

export function WindDirectionCard({ deg, windSpeed, loading }: WindDirectionCardProps) {
  return (
    <Card className="flex min-h-[118px] flex-col justify-between sm:min-h-[128px]">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
        Arah Angin
      </p>
      {loading ? (
        <div className="mt-2 h-8 w-24 animate-pulse rounded bg-[var(--color-border)]" />
      ) : deg == null ? (
        <EmptyState message="Tidak ada data" />
      ) : windSpeed === 0 || (deg === 0 && (windSpeed == null || windSpeed === 0)) ? (
        <>
          <p className="mt-1.5 text-lg font-semibold text-[var(--color-text)] sm:text-2xl">
            Tenang
          </p>
          <p className="mt-1.5 text-[11px] text-[var(--color-text-muted)] sm:text-xs">tidak ada angin</p>
        </>
      ) : (
        <>
          <p className="mt-1.5 text-base font-semibold leading-snug text-[var(--color-text)] sm:text-xl">
            {windCompassLabel(deg)}
          </p>
          <p className="mt-1.5 text-[11px] text-[var(--color-text-muted)] sm:text-xs">
            {windCompassShort(deg)} · {deg.toFixed(0)}°
          </p>
        </>
      )}
    </Card>
  );
}
