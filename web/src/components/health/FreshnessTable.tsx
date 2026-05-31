"use client";

import type { HealthStream } from "@/lib/types";
import { StatusDot } from "@/components/common/StatusDot";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

function fmtAge(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}d`;
}

function fmtTs(ts: string | null): string {
  if (!ts) return "—";
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function streamKindLabel(kind: HealthStream["kind"]): string {
  return kind === "event" ? "aktivitas" : "periodik";
}

function statusLabel(status: HealthStream["status"]): string {
  const labels: Record<HealthStream["status"], string> = {
    fresh: "fresh",
    stale: "stale",
    offline: "offline",
    no_data: "no data",
    idle: "idle",
    unknown: "unknown",
  };
  return labels[status];
}

interface FreshnessTableProps {
  streams: HealthStream[];
  loading: boolean;
}

export function FreshnessTable({ streams, loading }: FreshnessTableProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-40 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  return (
    <Card>
      <p className="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Kesegaran Data
      </p>
      {streams.length === 0 ? (
        <EmptyState message="Tidak ada data stream" detail="Data kesegaran akan muncul setelah sinkronisasi pertama." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="pb-2 text-left text-xs font-medium text-[var(--color-text-muted)]">
                  Tabel
                </th>
                <th className="pb-2 text-left text-xs font-medium text-[var(--color-text-muted)]">
                  Terakhir Dilihat
                </th>
                <th className="pb-2 text-right text-xs font-medium text-[var(--color-text-muted)]">
                  Usia
                </th>
                <th className="pb-2 text-right text-xs font-medium text-[var(--color-text-muted)]">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {streams.map((stream) => (
                <tr
                  key={stream.table}
                  className="border-b border-[var(--color-border)] last:border-0"
                >
                  <td className="py-2">
                    <div className="font-mono text-xs text-[var(--color-text)]">
                      {stream.table}
                    </div>
                    <div className="mt-0.5 text-[11px] text-[var(--color-text-muted)]">
                      {streamKindLabel(stream.kind)}
                    </div>
                  </td>
                  <td className="py-2 text-[var(--color-text)]">{fmtTs(stream.last_ts_utc)}</td>
                  <td className="py-2 text-right text-[var(--color-text-muted)]">
                    {fmtAge(stream.age_seconds)}
                  </td>
                  <td className="py-2 text-right">
                    <span className="inline-flex items-center justify-end gap-1.5">
                      <StatusDot status={stream.status} pulse={stream.status === "fresh"} />
                      <span className="text-xs text-[var(--color-text-muted)]">
                        {statusLabel(stream.status)}
                      </span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
