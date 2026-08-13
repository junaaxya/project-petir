"use client";
import type { PaginationMeta, QualityEvent } from "@/lib/api";
import type { QualityStatus } from "@contracts";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";
import { PaginationControls } from "@/components/common/PaginationControls";
import { qualityStatusLabel } from "@/lib/uiLabels";

const STATUS_STYLES: Record<QualityStatus, string> = {
  ok: "bg-green-900/40 text-green-400",
  warn: "bg-amber-900/40 text-amber-400",
  invalid: "bg-red-900/40 text-red-400",
};

const FILTER_OPTIONS: { label: string; value: QualityStatus | "all" }[] = [
  { label: "Semua", value: "all" },
  { label: "Baik", value: "ok" },
  { label: "Perlu perhatian", value: "warn" },
  { label: "Tidak valid", value: "invalid" },
];

function fmtTs(ts: string | null): string {
  if (!ts) return "—";
  return new Date(ts).toLocaleString("id-ID", {
    timeZone: "Asia/Jakarta",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }) + " WIB";
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

function formatQualityMessage(event: QualityEvent, codes: string[]): string {
  const raw = event.message?.trim();

  if (raw) {
    const normalized = raw.toLowerCase();
    if (normalized === "n/a" || normalized === "quality ok: n/a") {
      return "Tidak ada catatan tambahan.";
    }

    const qualityPrefix = /^quality\s+(ok|warn|invalid)\s*:\s*(.+)$/i.exec(raw);
    if (qualityPrefix) {
      const detail = qualityPrefix[2]?.trim();
      if (!detail || detail.toLowerCase() === "n/a") {
        return `Status kualitas data: ${qualityStatusLabel(event.quality_status)}.`;
      }
      return `${qualityStatusLabel(event.quality_status)}: ${formatReasonCode(detail)}.`;
    }
  }

  if (codes.length > 0) {
    return `${qualityStatusLabel(event.quality_status)}: ${codes.map(formatReasonCode).join(", ")}.`;
  }

  if (raw) return raw;
  return "Tidak ada catatan tambahan.";
}

interface QualityEventsTableProps {
  items: QualityEvent[];
  loading: boolean;
  filter: QualityStatus | "all";
  onFilterChange: (value: QualityStatus | "all") => void;
  pagination?: PaginationMeta | null;
  onPageChange?: (page: number) => void;
}

export function QualityEventsTable({
  items,
  loading,
  filter,
  onFilterChange,
  pagination = null,
  onPageChange,
}: QualityEventsTableProps) {

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
          Log Masalah Kualitas
        </p>
        <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-0.5">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onFilterChange(opt.value)}
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

      {items.length === 0 ? (
        <EmptyState
          message="Tidak ada riwayat kualitas data"
          detail="Tidak ada log masalah kualitas yang cocok dengan filter saat ini."
        />
      ) : (
        <>
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
                    Penyebab
                  </th>
                  <th className="pb-2 text-left text-xs font-medium text-[var(--color-text-muted)]">
                    Pesan
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((event) => {
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
                          {qualityStatusLabel(event.quality_status)}
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
                                className="inline-block rounded bg-red-900/30 px-1.5 py-0.5 text-xs text-red-300"
                              >
                                {formatReasonCode(code)}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td className="py-2 text-[var(--color-text)]">
                        {formatQualityMessage(event, codes)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {pagination && onPageChange && (
            <PaginationControls
              page={pagination.page}
              totalPages={pagination.total_pages}
              totalItems={pagination.total_items}
              pageSize={pagination.page_size}
              onPageChange={onPageChange}
            />
          )}
        </>
      )}
    </Card>
  );
}
