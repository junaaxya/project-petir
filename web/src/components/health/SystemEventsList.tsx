"use client";

import type { SystemEvent } from "@/lib/api";
import type { PaginationMeta } from "@/lib/api";
import type { SystemLevel } from "@contracts";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";
import { PaginationControls } from "@/components/common/PaginationControls";

const LIGHTNING_UNKNOWN_GROUP_WINDOW_MS = 5 * 60 * 1000;
const HEARTBEAT_GROUP_WINDOW_MS = 5 * 60 * 1000;

type DisplayEvent = SystemEvent & {
  __groupItems?: SystemEvent[];
};

const LEVEL_COLORS: Record<SystemLevel, string> = {
  debug: "text-slate-400",
  info: "text-blue-400",
  warn: "text-amber-400",
  error: "text-red-400",
  critical: "text-red-300 font-semibold",
};

const LEVEL_BADGES: Record<SystemLevel, string> = {
  debug: "bg-slate-900/50 text-slate-300 border-slate-700",
  info: "bg-blue-900/30 text-blue-300 border-blue-800",
  warn: "bg-amber-900/30 text-amber-300 border-amber-800",
  error: "bg-red-900/30 text-red-300 border-red-800",
  critical: "bg-red-900/50 text-red-200 border-red-700",
};

const LEVEL_LABELS: Record<SystemLevel, string> = {
  debug: "Debug",
  info: "Info",
  warn: "Peringatan",
  error: "Error",
  critical: "Kritis",
};

function fmtTs(ts: string): string {
  return new Date(ts).toLocaleString("id-ID", {
    timeZone: "Asia/Jakarta",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatEventType(value: string | null): string {
  if (!value) return "Peristiwa sistem";

  const knownLabels: Record<string, string> = {
    lightning_unknown: "Sinyal petir tidak dikenal",
    node_online: "Sensor kembali online",
    node_offline: "Sensor offline",
  };

  if (knownLabels[value]) return knownLabels[value];

  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatSource(value: string | null): string {
  if (!value) return "Sumber tidak diketahui";

  const knownLabels: Record<string, string> = {
    lightning_ingest: "Ingest sensor petir",
    weather_ingest: "Ingest sensor cuaca",
    "server-monitor": "Pemantau server",
  };

  if (knownLabels[value]) return knownLabels[value];

  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function titleCase(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function parseEventPayload(event: SystemEvent): Record<string, unknown> | null {
  if (!event.message) return null;
  try {
    return JSON.parse(event.message) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function isLightningUnknownEvent(event: SystemEvent): boolean {
  return event.event_type === "lightning_unknown";
}

function buildLightningUnknownGroupMessage(events: SystemEvent[]): string {
  const firstPayload = parseEventPayload(events[0]);
  const sensor = typeof firstPayload?.sensor === "string" ? firstPayload.sensor : "Sensor petir";
  const mode = typeof firstPayload?.mode === "string" ? firstPayload.mode : null;
  const count = events.length;
  const signalLabel = count === 1 ? "1 sinyal tidak dikenal" : `${count} sinyal tidak dikenal`;

  return mode
    ? `${sensor} mendeteksi ${signalLabel} dalam 5 menit terakhir pada mode ${mode}.`
    : `${sensor} mendeteksi ${signalLabel} dalam 5 menit terakhir.`;
}

function isHeartbeatEvent(event: SystemEvent): boolean {
  return event.event_type === "ingest_heartbeat";
}

function buildHeartbeatGroupMessage(events: SystemEvent[]): string {
  const first = events[0];
  const source = formatSource(first?.source ?? null);
  const count = events.length;
  return count === 1
    ? `${source} mengirim 1 heartbeat dalam 5 menit terakhir.`
    : `${source} mengirim ${count} heartbeat dalam 5 menit terakhir.`;
}

function aggregateEvents(
  items: SystemEvent[],
  aggregateWarnings: boolean,
  aggregateRoutineInfo: boolean,
): DisplayEvent[] {
  if (!aggregateWarnings && !aggregateRoutineInfo) {
    return items.map((event) => ({ ...event }));
  }

  const aggregated: DisplayEvent[] = [];

  for (const event of items) {
    if (aggregateRoutineInfo && isHeartbeatEvent(event)) {
      let merged = false;

      for (const existing of aggregated) {
        if (!isHeartbeatEvent(existing)) continue;
        const sameSource = (existing.source ?? null) === (event.source ?? null);
        const existingTs = new Date(existing.ts_pi_utc).getTime();
        const currentTs = new Date(event.ts_pi_utc).getTime();
        const withinWindow =
          Number.isFinite(existingTs) &&
          Number.isFinite(currentTs) &&
          Math.abs(existingTs - currentTs) <= HEARTBEAT_GROUP_WINDOW_MS;

        if (!sameSource || !withinWindow) continue;

        const existingGroup = existing.__groupItems ? [...existing.__groupItems] : [{ ...existing }];
        existingGroup.push(event);
        existing.__groupItems = existingGroup;
        existing.message = buildHeartbeatGroupMessage(existingGroup);
        if (currentTs > existingTs) {
          existing.ts_pi_utc = event.ts_pi_utc;
          existing.edge_id = event.edge_id;
        }
        merged = true;
        break;
      }

      if (!merged) {
        aggregated.push({ ...event, message: buildHeartbeatGroupMessage([event]) });
      }
      continue;
    }

    if (!isLightningUnknownEvent(event)) {
      aggregated.push({ ...event });
      continue;
    }

    const currentPayload = parseEventPayload(event);
    let merged = false;

    for (const existing of aggregated) {
      if (!isLightningUnknownEvent(existing)) continue;

      const existingPayload = parseEventPayload(existing);
      const sameSensor = (currentPayload?.sensor ?? null) === (existingPayload?.sensor ?? null);
      const sameMode = (currentPayload?.mode ?? null) === (existingPayload?.mode ?? null);
      const existingTs = new Date(existing.ts_pi_utc).getTime();
      const currentTs = new Date(event.ts_pi_utc).getTime();
      const withinWindow = Number.isFinite(existingTs) && Number.isFinite(currentTs) && Math.abs(existingTs - currentTs) <= LIGHTNING_UNKNOWN_GROUP_WINDOW_MS;

      if (!sameSensor || !sameMode || !withinWindow) continue;

      const existingGroup = existing.__groupItems ? [...existing.__groupItems] : [{ ...existing }];
      existingGroup.push(event);
      existing.__groupItems = existingGroup;
      existing.message = buildLightningUnknownGroupMessage(existingGroup);
      if (currentTs > existingTs) {
        existing.ts_pi_utc = event.ts_pi_utc;
        existing.edge_id = event.edge_id;
      }
      merged = true;
      break;
    }

    if (!merged) {
      aggregated.push({ ...event });
    }
  }

  return aggregated.sort((a, b) => new Date(b.ts_pi_utc).getTime() - new Date(a.ts_pi_utc).getTime());
}

function formatMessage(event: DisplayEvent): string {
  if (!event.message) return "Detail masalah tidak tersedia.";

  if (event.__groupItems && event.__groupItems.length > 1 && event.event_type === "lightning_unknown") {
    return event.message;
  }

  try {
    const parsed = JSON.parse(event.message) as Record<string, unknown>;

    if (event.event_type === "lightning_unknown") {
      const sensor = typeof parsed.sensor === "string" ? parsed.sensor : "sensor petir";
      const mode = typeof parsed.mode === "string" ? parsed.mode : null;
      return mode
        ? `${sensor} mendeteksi sinyal yang tidak dikenali pada mode ${mode}.`
        : `${sensor} mendeteksi sinyal yang tidak dikenali.`;
    }

    const entries = Object.entries(parsed)
      .filter(([, value]) => value != null && value !== "")
      .map(([key, value]) => `${titleCase(key)}: ${String(value)}`);

    if (entries.length > 0) return entries.join(" • ");
  } catch {
    // fall back to raw message below
  }

  return event.message;
}

interface SystemEventsListProps {
  items: SystemEvent[];
  loading: boolean;
  title?: string;
  description?: string;
  emptyMessage?: string;
  emptyDetail?: string;
  aggregateWarnings?: boolean;
  aggregateRoutineInfo?: boolean;
  pagination?: PaginationMeta | null;
  onPageChange?: (page: number) => void;
  filterOptions?: Array<{ value: string; label: string }>;
  activeFilter?: string;
  onFilterChange?: (value: string) => void;
}

export function SystemEventsList({
  items,
  loading,
  title = "Log Masalah Terbaru",
  description = "Menampilkan perubahan status sensor, peringatan, dan error penting. Heartbeat rutin disembunyikan agar lebih mudah dipantau.",
  emptyMessage = "Tidak ada peringatan sistem",
  emptyDetail = "Belum ada perubahan status sensor, warning, error, atau kondisi kritis terbaru.",
  aggregateWarnings = true,
  aggregateRoutineInfo = false,
  pagination = null,
  onPageChange,
  filterOptions,
  activeFilter,
  onFilterChange,
}: SystemEventsListProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-40 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const displayItems = aggregateEvents(items, aggregateWarnings, aggregateRoutineInfo);

  return (
    <Card>
      <div className="mb-3 flex flex-col gap-1">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          {title}
        </p>
        <p className="text-xs text-[var(--color-text-muted)]">{description}</p>
        {filterOptions && filterOptions.length > 0 && onFilterChange && (
          <div className="mt-2 flex flex-wrap gap-2">
            {filterOptions.map((option) => {
              const active = option.value === activeFilter;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => onFilterChange(option.value)}
                  className={[
                    "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                    active
                      ? "border-blue-700 bg-blue-900/30 text-blue-200"
                      : "border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)]",
                  ].join(" ")}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        )}
      </div>
      {displayItems.length === 0 ? (
        <EmptyState message={emptyMessage} detail={emptyDetail} />
      ) : (
        <>
          <ul className="flex flex-col gap-3">
            {displayItems.map((event) => {
              const levelColor = event.level ? LEVEL_COLORS[event.level] : "text-[var(--color-text-muted)]";
              const levelBadge = event.level ? LEVEL_BADGES[event.level] : "bg-gray-800/60 text-gray-400 border-gray-700";
              const groupedCount = event.__groupItems?.length ?? 1;
              return (
                <li
                  key={`${event.edge_id}-${event.ts_pi_utc}`}
                  className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]/40 p-3"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex min-w-0 flex-col gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase ${levelBadge}`}>
                          {event.level ? LEVEL_LABELS[event.level] : "—"}
                        </span>
                        <span className={`text-xs font-medium ${levelColor}`}>
                          {formatEventType(event.event_type)}
                        </span>
                        {groupedCount > 1 && (
                          <span className="inline-flex rounded-full border border-amber-800 bg-amber-900/20 px-2 py-0.5 text-[11px] font-medium text-amber-300">
                            {groupedCount} kejadian
                          </span>
                        )}
                      </div>
                      {event.message && (
                        <p className="text-sm leading-relaxed text-[var(--color-text)] break-words">{formatMessage(event)}</p>
                      )}
                      <span className="text-xs text-[var(--color-text-muted)]">
                        Sumber: {formatSource(event.source)}
                      </span>
                    </div>
                    <span className="shrink-0 text-xs text-[var(--color-text-muted)]">
                      {fmtTs(event.ts_pi_utc)} WIB
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
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
