"use client";

import type { LightningLatestMinute } from "@/lib/api";
import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";

function fmtTs(ts: string | null): string {
  if (!ts) return "—";
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

interface LastEventCardProps {
  minute: LightningLatestMinute | null;
  loading: boolean;
}

export function LastEventCard({ minute, loading }: LastEventCardProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-28 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const hasEvent = minute?.last_event_ts_utc != null;

  return (
    <Card>
      <p className="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Kejadian Terakhir
      </p>
      {!hasEvent ? (
        <EmptyState message="Belum ada kejadian" detail="Kejadian petir akan muncul di sini setelah terdeteksi." />
      ) : (
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
          <div>
            <dt className="text-xs text-[var(--color-text-muted)]">Waktu</dt>
            <dd className="mt-0.5 text-sm font-medium text-[var(--color-text)]">
              {fmtTs(minute!.last_event_ts_utc)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-[var(--color-text-muted)]">Jarak</dt>
            <dd className="mt-0.5 text-sm font-medium text-[var(--color-text)]">
              {minute!.last_distance_km != null ? `${minute!.last_distance_km} km` : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-[var(--color-text-muted)]">Energi Maks</dt>
            <dd className="mt-0.5 text-sm font-medium text-[var(--color-text)]">
              {minute!.max_energy_raw != null ? String(minute!.max_energy_raw) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-[var(--color-text-muted)]">Sumber</dt>
            <dd className="mt-0.5 text-sm font-medium text-[var(--color-text)]">
              {minute!.source ?? "—"}
            </dd>
          </div>
        </dl>
      )}
    </Card>
  );
}
