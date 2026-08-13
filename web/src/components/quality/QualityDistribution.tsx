"use client";

import type { QualityEvent, QualitySummary } from "@/lib/api";
import type { QualityStatus } from "@contracts";
import { Card } from "@/components/common/Card";
import { qualityStatusLabel } from "@/lib/uiLabels";

const STATUS_COLORS: Record<QualityStatus, string> = {
  ok: "bg-green-900/40 text-green-400",
  warn: "bg-amber-900/40 text-amber-400",
  invalid: "bg-red-900/40 text-red-400",
};

interface QualityDistributionProps {
  items: QualityEvent[];
  summary: QualitySummary | null;
  loading: boolean;
}

export function QualityDistribution({ items, summary, loading }: QualityDistributionProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-28 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const counts: Record<QualityStatus, number> = {
    ok: summary?.effective_counts?.ok ?? summary?.counts.ok ?? 0,
    warn: summary?.effective_counts?.warn ?? summary?.counts.warn ?? 0,
    invalid: summary?.effective_counts?.invalid ?? summary?.counts.invalid ?? 0,
  };

  const total = summary?.total_minutes ?? 0;
  const okPercent = total > 0 ? Math.round((counts.ok / total) * 100) : null;
  const warnPercent = total > 0 ? Math.round((counts.warn / total) * 100) : null;
  const invalidPercent = total > 0 ? Math.round((counts.invalid / total) * 100) : null;
  return (
    <Card>
      <div className="mb-4 flex flex-col gap-1">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Ringkasan Kualitas Data
        </p>
        <p className="text-xs text-[var(--color-text-muted)]">
          Gambaran cepat kualitas data pada rentang waktu yang dipilih, termasuk menit yang tercatat bermasalah pada log kualitas.
        </p>
      </div>

      {total === 0 ? (
        <div className="flex flex-col gap-2">
          <span className="text-2xl font-semibold text-[var(--color-text)]">Belum ada data</span>
          <p className="text-sm text-[var(--color-text-muted)]">
            Belum ada minute summary cuaca untuk diringkas pada rentang waktu ini.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/40 p-4">
            <span
              className={`inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS.ok}`}
            >
              {qualityStatusLabel("ok")}
            </span>
            <div className="flex flex-col gap-1">
              <span className="text-2xl font-semibold text-[var(--color-text)]">
                {okPercent}% data baik
              </span>
              <p className="text-sm text-[var(--color-text-muted)]">
                {counts.warn === 0 && counts.invalid === 0
                  ? "Semua data pada rentang waktu ini berada dalam kondisi baik."
                  : counts.warn > 0 && counts.invalid > 0
                    ? `${warnPercent}% data perlu perhatian dan ${invalidPercent}% data tidak valid.`
                    : counts.warn > 0
                      ? `${warnPercent}% data perlu perhatian. Tidak ada data tidak valid.`
                      : `${invalidPercent}% data tidak valid. Tidak ada data yang hanya perlu perhatian.`}
              </p>
              <p className="text-xs text-[var(--color-text-muted)]">
                {`${counts.ok} dari ${total} menit data berada dalam kondisi baik setelah memasukkan menit yang tercatat bermasalah.`}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {(["ok", "warn", "invalid"] as QualityStatus[]).map((s) => (
              <div key={s} className="flex flex-col gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]/30 p-3">
                <span
                  className={`inline-flex w-fit items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[s]}`}
                >
                  {qualityStatusLabel(s)}
                </span>
                <span className="text-xl font-bold text-[var(--color-text)]">{counts[s]} menit</span>
                <span className="text-xs text-[var(--color-text-muted)]">
                  {`${Math.round((counts[s] / total) * 100)}% dari total menit data`}
                </span>
              </div>
            ))}
          </div>

          {items.length > 0 ? (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]/20 p-3">
              <p className="text-xs font-medium text-[var(--color-text)]">
                Ringkasan di atas sudah memasukkan log masalah pada rentang waktu yang dipilih.
              </p>
              <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                Jika pada hari atau rentang waktu ini ada menit yang tercatat memiliki masalah kualitas, menit tersebut ikut dihitung pada ringkasan atas sebagai perlu perhatian atau tidak valid agar hasilnya tidak membingungkan.
              </p>
            </div>
          ) : null}
        </div>
      )}
    </Card>
  );
}
