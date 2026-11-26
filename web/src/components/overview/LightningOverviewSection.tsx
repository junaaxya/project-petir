"use client";

import Link from "next/link";
import { Card } from "@/components/common/Card";
import { Badge } from "@/components/common/Badge";
import { LastEventCard } from "@/components/lightning/LastEventCard";
import { LightningStatusBadge } from "@/components/lightning/LightningStatusBadge";
import type { LightningLatestResponse } from "@/lib/api";
import type { NodeStatus } from "@/lib/types";
import { isRealtimeUnavailable, realtimeSnapshotDetail } from "@/lib/realtime";

interface LightningOverviewSectionProps {
  lightning: LightningLatestResponse | undefined;
  lightningLoading: boolean;
  nodeStatus: NodeStatus | undefined;
}

function CountStat({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/70 px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">{label}</p>
      <p className="mt-1 text-lg font-semibold text-[var(--color-text)]">{value ?? "—"}</p>
    </div>
  );
}

export function LightningOverviewSection({ lightning, lightningLoading, nodeStatus }: LightningOverviewSectionProps) {
  const minute = lightning?.minute ?? null;
  const realtimeUnavailable = isRealtimeUnavailable(nodeStatus);
  const snapshotDetail = realtimeSnapshotDetail(nodeStatus, minute?.minute_utc);
  const hasValidObservation = minute != null && minute.status != null && minute.status !== "no_data";

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-[var(--color-text)] sm:text-lg">Petir Saat Ini</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Status cepat petir langsung di Ringkasan, detail lengkap tetap ada di halaman Petir.
          </p>
        </div>
        <Link
          href="/lightning"
          className="shrink-0 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm font-medium text-[var(--color-text)] transition-colors hover:border-blue-500 hover:text-blue-400"
        >
          Detail petir →
        </Link>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <Card className="flex flex-col gap-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex flex-col gap-2">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                Status Petir
              </p>
              {lightningLoading ? (
                <div className="h-10 w-36 animate-pulse rounded-2xl bg-[var(--color-border)]" />
              ) : realtimeUnavailable ? (
                <Badge variant="offline" label="Offline" />
              ) : (
                <LightningStatusBadge status={minute?.status ?? null} large />
              )}
            </div>

            <div className="max-w-sm rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/60 px-3 py-2 text-sm text-[var(--color-text-muted)]">
              {lightningLoading ? (
                <div className="h-10 w-48 animate-pulse rounded bg-[var(--color-border)]" />
              ) : realtimeUnavailable ? (
                <>
                  <p className="font-medium text-[var(--color-text)]">Sensor sedang offline</p>
                  <p>{snapshotDetail ?? "Status realtime belum tersedia."}</p>
                </>
              ) : !hasValidObservation ? (
                <>
                  <p className="font-medium text-[var(--color-text)]">Belum ada pengamatan petir yang valid</p>
                  <p>Jumlah kejadian tetap ditampilkan sebagai tanda pisah, bukan nol.</p>
                </>
              ) : minute.last_event_ts_utc ? (
                <>
                  <p className="font-medium text-[var(--color-text)]">Aktivitas terbaru terdeteksi</p>
                  <p>
                    {minute.last_distance_km != null ? `${minute.last_distance_km} km` : "Jarak tidak diketahui"}
                    {" • "}
                    {snapshotDetail ?? `Diperbarui ${new Date(minute.last_event_ts_utc).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}`}
                  </p>
                </>
              ) : (
                <>
                  <p className="font-medium text-[var(--color-text)]">Belum ada kejadian terbaru</p>
                  <p>Pantau status di bawah untuk melihat aktivitas petir, gangguan, atau derau terbaru.</p>
                </>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <CountStat label="Petir" value={minute?.lightning_count} />
            <CountStat label="Gangguan" value={minute?.disturber_count} />
            <CountStat label="Derau" value={minute?.noise_event_count} />
          </div>

          <div className="rounded-xl border border-dashed border-[var(--color-border)] px-3 py-3 text-sm text-[var(--color-text-muted)]">
            <span className="font-medium text-[var(--color-text)]">Tips cepat:</span>{" "}
            {hasValidObservation ? (
              <>
                saat badge berubah dari
                <span className="mx-1 font-medium text-green-400">Tenang</span>
                ke status lain, pengguna bisa langsung melihat detail kejadiannya di bawah tanpa pindah halaman.
              </>
            ) : (
              "status aktivitas hanya ditampilkan setelah sensor memiliki pengamatan yang valid."
            )}
          </div>
        </Card>

        <LastEventCard minute={minute} loading={lightningLoading} offlineDetail={snapshotDetail} />
      </div>

    </section>
  );
}
