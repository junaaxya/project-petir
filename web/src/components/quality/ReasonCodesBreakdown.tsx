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

interface ReasonCodesBreakdownProps {
  items: QualityEvent[];
  loading: boolean;
}

export function ReasonCodesBreakdown({ items, loading }: ReasonCodesBreakdownProps) {
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
      <p className="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Kode Alasan
      </p>
      {sorted.length === 0 ? (
        <EmptyState message="Tidak ada kode alasan" detail="Kode alasan muncul saat masalah kualitas terdeteksi." />
      ) : (
        <ul className="flex flex-col gap-2">
          {sorted.map(([code, count]) => (
            <li key={code} className="flex min-w-0 flex-col gap-1">
              <div className="flex min-w-0 items-center justify-between gap-2">
                <span className="min-w-0 break-all font-mono text-xs text-[var(--color-text)]">
                  {code}
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
