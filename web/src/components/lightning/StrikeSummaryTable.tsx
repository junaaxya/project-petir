"use client";

import type { LightningEvent } from "@/lib/api";
import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";
import { InfoTooltip } from "@/components/common/InfoTooltip";

interface StrikeSummaryTableProps {
  items: LightningEvent[];
  loading: boolean;
}

function fmtTs(ts: string): string {
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const CHIP_RED = "bg-red-900/40 text-red-400 border-red-800";
const CHIP_AMBER = "bg-amber-900/40 text-amber-400 border-amber-800";
const CHIP_SLATE = "bg-slate-800/60 text-slate-400 border-slate-700";

function proximityLabel(km: number): { text: string; chip: string } {
  if (km < 5) return { text: "Sangat dekat", chip: CHIP_RED };
  if (km <= 15) return { text: "Dekat", chip: CHIP_AMBER };
  return { text: "Jauh", chip: CHIP_SLATE };
}

function strengthLabel(ratio: number): { text: string; chip: string } {
  if (ratio >= 0.66) return { text: "Kuat", chip: CHIP_RED };
  if (ratio >= 0.33) return { text: "Sedang", chip: CHIP_AMBER };
  return { text: "Lemah", chip: CHIP_SLATE };
}

const CHIP_BASE =
  "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium";

export function StrikeSummaryTable({ items, loading }: StrikeSummaryTableProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-48 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const strikes = [...items.filter((e) => e.event_type === "lightning")].sort(
    (a, b) => new Date(b.ts_pi_utc).getTime() - new Date(a.ts_pi_utc).getTime(),
  );

  const maxEnergy = strikes.reduce<number | null>((acc, e) => {
    if (e.energy_raw == null) return acc;
    return acc == null ? e.energy_raw : Math.max(acc, e.energy_raw);
  }, null);

  const n = strikes.length;

  return (
    <Card>
      <div className="mb-3 flex items-center gap-2">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Ringkasan Sambaran Petir
          <span className="ml-2 font-normal normal-case">({n} sambaran)</span>
        </p>
        <InfoTooltip
          text="Hanya menampilkan sambaran petir asli. Gangguan dan derau tidak termasuk."
          label="Keterangan tabel"
        />
      </div>

      {n === 0 ? (
        <EmptyState
          message="Belum ada sambaran petir"
          detail="Pada rentang waktu ini sensor tidak mendeteksi sambaran petir asli (hanya gangguan/derau, atau tidak ada aktivitas)."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">
                  Waktu
                </th>
                <th className="py-2 text-right text-xs font-medium text-[var(--color-text-muted)]">
                  Jarak
                </th>
                <th className="py-2 text-right text-xs font-medium text-[var(--color-text-muted)]">
                  <span className="inline-flex items-center gap-1">
                    Energi
                    <InfoTooltip
                      text="Nilai energi relatif dari sensor AS3935 (bukan satuan Joule). Hanya untuk membandingkan kekuatan antar sambaran."
                      label="Keterangan energi"
                    />
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {strikes.map((strike) => {
                const prox =
                  strike.distance_km != null
                    ? proximityLabel(strike.distance_km)
                    : null;

                const strength =
                  strike.energy_raw != null && maxEnergy != null && maxEnergy > 0
                    ? strengthLabel(strike.energy_raw / maxEnergy)
                    : null;

                return (
                  <tr
                    key={strike.edge_id}
                    className="border-b border-[var(--color-border)] last:border-0"
                  >
                    <td className="py-2 text-[var(--color-text)]">
                      {fmtTs(strike.ts_pi_utc)}
                    </td>
                    <td className="py-2 text-right text-[var(--color-text)]">
                      {prox != null && strike.distance_km != null ? (
                        <span className="inline-flex flex-col items-end gap-1">
                          <span className="font-mono">{strike.distance_km} km</span>
                          <span className={`${CHIP_BASE} ${prox.chip}`}>{prox.text}</span>
                        </span>
                      ) : (
                        <span className="text-[var(--color-text-muted)]">—</span>
                      )}
                    </td>
                    <td className="py-2 text-right text-[var(--color-text)]">
                      {strength != null && strike.energy_raw != null ? (
                        <span className="inline-flex flex-col items-end gap-1">
                          <span className="font-mono">{strike.energy_raw}</span>
                          <span className={`${CHIP_BASE} ${strength.chip}`}>{strength.text}</span>
                        </span>
                      ) : (
                        <span className="text-[var(--color-text-muted)]">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
