"use client";

import type { QualityEvent } from "@/lib/api";
import type { QualityStatus } from "@contracts";
import { Card } from "@/components/common/Card";

const STATUS_COLORS: Record<QualityStatus, string> = {
  ok: "bg-green-900/40 text-green-400",
  warn: "bg-amber-900/40 text-amber-400",
  invalid: "bg-red-900/40 text-red-400",
};

interface QualityDistributionProps {
  items: QualityEvent[];
  loading: boolean;
}

export function QualityDistribution({ items, loading }: QualityDistributionProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-20 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const counts: Record<QualityStatus, number> = { ok: 0, warn: 0, invalid: 0 };
  for (const item of items) {
    if (item.quality_status) counts[item.quality_status]++;
  }

  const total = items.length;

  return (
    <Card>
      <p className="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Distribusi
      </p>
      <div className="flex flex-wrap gap-4">
        {(["ok", "warn", "invalid"] as QualityStatus[]).map((s) => (
          <div key={s} className="flex flex-col gap-1">
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[s]}`}
            >
              {s}
            </span>
            <span className="text-xl font-bold text-[var(--color-text)]">{counts[s]}</span>
            <span className="text-xs text-[var(--color-text-muted)]">
              {total > 0 ? `${Math.round((counts[s] / total) * 100)}%` : "—"}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
