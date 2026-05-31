"use client";

import type { IngestRun } from "@/lib/api";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

function calcSuccessRate(runs: IngestRun[]): string {
  if (runs.length === 0) return "—";
  const successful = runs.filter((r) => r.status === "accepted").length;
  return `${Math.round((successful / runs.length) * 100)}%`;
}

interface BatchSuccessRateProps {
  runs: IngestRun[];
  loading: boolean;
}

export function BatchSuccessRate({ runs, loading }: BatchSuccessRateProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-24 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const rate = calcSuccessRate(runs);
  const totalAccepted = runs.reduce((sum, r) => sum + r.accepted, 0);
  const totalRejected = runs.reduce((sum, r) => sum + r.rejected, 0);

  return (
    <Card>
      <p className="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Tingkat Keberhasilan Batch
      </p>
      {runs.length === 0 ? (
        <EmptyState message="Tidak ada proses ingest" detail="Riwayat proses akan muncul setelah sinkronisasi pertama." />
      ) : (
        <div className="flex flex-wrap gap-6">
          <div>
            <p className="text-2xl font-bold text-[var(--color-text)]">{rate}</p>
            <p className="text-xs text-[var(--color-text-muted)]">
              {runs.filter((r) => r.status === "accepted").length} / {runs.length} proses diterima
            </p>
          </div>
          <div>
            <p className="text-2xl font-bold text-green-400">{totalAccepted.toLocaleString()}</p>
            <p className="text-xs text-[var(--color-text-muted)]">baris diterima</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-red-400">{totalRejected.toLocaleString()}</p>
            <p className="text-xs text-[var(--color-text-muted)]">baris ditolak</p>
          </div>
        </div>
      )}
    </Card>
  );
}
