"use client";

import type { QualityEvent } from "@/lib/api";
import { Card } from "@/components/common/Card";
import { EmptyState } from "@/components/common/EmptyState";

function parseReasonCodes(codes: string | string[] | null): string[] {
  if (!codes) return [];
  if (Array.isArray(codes)) return codes.filter(Boolean);
  try {
    const parsed = JSON.parse(codes);
    if (Array.isArray(parsed)) return (parsed as string[]).filter(Boolean);
  } catch (_e) {
    void _e;
  }
  return codes
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function formatReasonCode(code: string): string {
  const labels: Record<string, string> = {
    humidity_spike: "Kelembaban berubah tiba-tiba",
    out_of_range: "Nilai di luar batas wajar",
    stale_reading: "Data sensor sudah terlalu lama",
    missing_temp: "Suhu tidak tersedia",
    missing_humidity: "Kelembaban tidak tersedia",
    missing_pressure: "Tekanan udara tidak tersedia",
    invalid_humidity_range: "Rentang kelembaban tidak valid",
    invalid_temp_range: "Rentang suhu tidak valid",
    invalid_pressure_range: "Rentang tekanan udara tidak valid",
  };

  if (labels[code]) return labels[code];

  return code
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

interface ReasonCodesBreakdownProps {
  items: QualityEvent[];
  loading: boolean;
  description?: string;
}

export function ReasonCodesBreakdown({
  items,
  loading,
  description = "Menampilkan penyebab yang paling sering muncul pada log masalah kualitas yang sedang ditampilkan.",
}: ReasonCodesBreakdownProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-24 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const codeCounts: Record<string, number> = {};
  for (const item of items) {
    for (const code of parseReasonCodes(item.reason_codes)) {
      codeCounts[code] = (codeCounts[code] ?? 0) + 1;
    }
  }

  const sorted = Object.entries(codeCounts).sort((a, b) => b[1] - a[1]);
  const maxCount = sorted[0]?.[1] ?? 1;

  return (
    <Card>
      <div className="mb-3 flex flex-col gap-1">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Penyebab Masalah yang Paling Sering
        </p>
        <p className="text-xs text-[var(--color-text-muted)]">
          {description}
        </p>
      </div>
      {sorted.length === 0 ? (
        <EmptyState
          message="Belum ada penyebab yang tercatat"
          detail="Penyebab akan muncul ketika sistem menemukan masalah pada kualitas data."
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {sorted.map(([code, count]) => (
            <li key={code} className="flex min-w-0 flex-col gap-1">
              <div className="flex min-w-0 items-center justify-between gap-2">
                <span className="min-w-0 text-xs text-[var(--color-text)]">
                  {formatReasonCode(code)}
                </span>
                <span className="shrink-0 text-xs font-medium tabular-nums text-[var(--color-text-muted)]">
                  {count}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--color-border)]">
                <div
                  className="h-full rounded-full bg-red-500/50"
                  style={{ width: `${(count / maxCount) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
