import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";

const COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

function toCompass(deg: number): string {
  const idx = Math.round((((deg % 360) + 360) % 360) / 45) % 8;
  return COMPASS[idx];
}

interface WindDirectionCardProps {
  deg: number | null | undefined;
  windSpeed: number | null | undefined;
  loading?: boolean;
}

export function WindDirectionCard({ deg, windSpeed, loading }: WindDirectionCardProps) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Arah Angin
      </p>
      {loading ? (
        <div className="mt-2 h-8 w-24 animate-pulse rounded bg-[var(--color-border)]" />
      ) : deg == null ? (
        <EmptyState message="Tidak ada data" />
      ) : windSpeed === 0 || (deg === 0 && (windSpeed == null || windSpeed === 0)) ? (
        <>
          <p className="mt-1 font-mono text-3xl font-semibold text-[var(--color-text)]">
            Tenang
          </p>
          <p className="mt-1 font-mono text-xs text-[var(--color-text-muted)]">tidak ada angin</p>
        </>
      ) : (
        <>
          <p className="mt-1 font-mono text-3xl font-semibold text-[var(--color-text)]">
            {toCompass(deg)}
          </p>
          <p className="mt-1 font-mono text-xs text-[var(--color-text-muted)]">{deg}°</p>
        </>
      )}
    </Card>
  );
}
