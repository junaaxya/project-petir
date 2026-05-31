"use client";

import type { SystemEvent } from "@/lib/api";
import type { SystemLevel } from "@contracts";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

const LEVEL_COLORS: Record<SystemLevel, string> = {
  debug: "text-slate-400",
  info: "text-blue-400",
  warn: "text-amber-400",
  error: "text-red-400",
  critical: "text-red-300 font-semibold",
};

function fmtTs(ts: string): string {
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

interface SystemEventsListProps {
  items: SystemEvent[];
  loading: boolean;
}

export function SystemEventsList({ items, loading }: SystemEventsListProps) {
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
        Kejadian Sistem Terbaru
      </p>
      {items.length === 0 ? (
        <EmptyState message="Tidak ada kejadian sistem" detail="Kejadian akan muncul setelah node sinkronisasi." />
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((event) => {
            const levelColor = event.level ? LEVEL_COLORS[event.level] : "text-[var(--color-text-muted)]";
            return (
              <li
                key={event.edge_id}
                className="flex flex-col gap-0.5 border-b border-[var(--color-border)] pb-2 last:border-0 last:pb-0"
              >
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-medium uppercase ${levelColor}`}>
                    {event.level ?? "—"}
                  </span>
                  {event.event_type && (
                    <span className="text-xs text-[var(--color-text-muted)]">
                      {event.event_type}
                    </span>
                  )}
                  <span className="ml-auto text-xs text-[var(--color-text-muted)]">
                    {fmtTs(event.ts_pi_utc)}
                  </span>
                </div>
                {event.message && (
                  <p className="text-sm text-[var(--color-text)]">{event.message}</p>
                )}
                {event.source && (
                  <span className="text-xs text-[var(--color-text-muted)]">{event.source}</span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
