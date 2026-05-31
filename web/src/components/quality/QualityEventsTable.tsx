"use client";

import { useState } from "react";
import type { QualityEvent } from "@/lib/api";
import type { QualityStatus } from "@contracts";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

const STATUS_STYLES: Record<QualityStatus, string> = {
  ok: "bg-green-900/40 text-green-400",
  warn: "bg-amber-900/40 text-amber-400",
  invalid: "bg-red-900/40 text-red-400",
};

const FILTER_OPTIONS: { label: string; value: QualityStatus | "all" }[] = [
  { label: "Semua", value: "all" },
  { label: "OK", value: "ok" },
  { label: "Peringatan", value: "warn" },
  { label: "Tidak Valid", value: "invalid" },
];

function fmtTs(ts: string | null): string {
  if (!ts) return "—";
  return new Date(ts).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

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

interface QualityEventsTableProps {
  items: QualityEvent[];
  loading: boolean;
}

export function QualityEventsTable({ items, loading }: QualityEventsTableProps) {
  const [filter, setFilter] = useState<QualityStatus | "all">("all");

  const filtered =
    filter === "all" ? items : items.filter((e) => e.quality_status === filter);

  if (loading) {
    return (
      <Card>
        <div className="h-48 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Kejadian Kualitas
        </p>
        <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-0.5">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setFilter(opt.value)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                filter === opt.value
                  ? "bg-blue-600 text-white"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState message="Tidak ada kejadian kualitas" detail="Tidak ada kejadian yang cocok dengan filter saat ini." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="pb-2 text-left text-xs font-medium text-[var(--color-text-muted)]">
                  Menit
                </th>
                <th className="pb-2 text-left text-xs font-medium text-[var(--color-text-muted)]">
                  Status
                </th>
                <th className="pb-2 text-left text-xs font-medium text-[var(--color-text-muted)]">
                  Kode Alasan
                </th>
                <th className="pb-2 text-left text-xs font-medium text-[var(--color-text-muted)]">
                  Pesan
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((event) => {
                const statusStyle = event.quality_status
                  ? STATUS_STYLES[event.quality_status]
                  : "bg-gray-800/60 text-gray-400";
                const codes = parseReasonCodes(event.reason_codes);
                return (
                  <tr
                    key={event.edge_id}
                    className="border-b border-[var(--color-border)] last:border-0"
                  >
                    <td className="py-2 pr-3 text-[var(--color-text)]">{fmtTs(event.minute_utc)}</td>
                    <td className="py-2 pr-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusStyle}`}
                      >
                        {event.quality_status ?? "—"}
                      </span>
                    </td>
                    <td className="py-2 pr-3">
                      {codes.length === 0 ? (
                        <span className="text-xs text-[var(--color-text-muted)]">—</span>
                      ) : (
                        <div className="flex max-w-xs flex-wrap gap-1">
                          {codes.map((code) => (
                            <span
                              key={code}
                              className="inline-block break-all rounded bg-red-900/30 px-1.5 py-0.5 font-mono text-xs text-red-300"
                            >
                              {code}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="py-2 text-[var(--color-text)]">
                      {event.message ?? "—"}
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
