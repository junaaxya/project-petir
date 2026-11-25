"use client";

import { Card } from "@/components/common/Card";
import { Badge } from "@/components/common/Badge";
import { EmptyState } from "@/components/common/EmptyState";
import type { WanFailoverEvent, WanFailoverHealthCheck, WanFailoverStatus } from "@/lib/types";
import { formatRelativeFromIso } from "@/lib/realtime";

interface WanFailoverPanelProps {
  status: WanFailoverStatus | undefined;
  healthLoading: boolean;
}

type WanBadge = "ethernet-primary" | "wifi-fallback" | "unknown";

function badgeLabel(badge: WanBadge): string {
  switch (badge) {
    case "ethernet-primary":
      return "Ethernet utama";
    case "wifi-fallback":
      return "Wi‑Fi cadangan";
    default:
      return "Belum diketahui";
  }
}

function booleanBadge(ok: boolean | null | undefined): { label: string; className: string } {
  if (ok === true) {
    return {
      label: "OK",
      className: "border-green-500/30 bg-green-500/10 text-green-300",
    };
  }
  if (ok === false) {
    return {
      label: "FAIL",
      className: "border-red-500/30 bg-red-500/10 text-red-300",
    };
  }
  return {
    label: "Belum ada data",
    className: "border-slate-500/30 bg-slate-500/10 text-slate-300",
  };
}

function uplinkLabel(kind: string | null | undefined, iface: string | null | undefined): string {
  if (kind === "ethernet") return iface ? `Ethernet (${iface})` : "Ethernet";
  if (kind === "wifi") return iface ? `Wi‑Fi (${iface})` : "Wi‑Fi";
  return iface ? iface : "Belum diketahui";
}

function modeLabel(mode: string | null | undefined): string {
  if (mode === "prefer_eth") return "Prioritaskan Ethernet";
  if (mode === "prefer_wifi") return "Prioritaskan Wi‑Fi";
  return "Belum diketahui";
}

function eventTypeLabel(eventType: string | null | undefined): string {
  if (eventType === "failover_to_wifi") return "Pindah ke Wi‑Fi";
  if (eventType === "recover_to_ethernet") return "Kembali ke Ethernet";
  if (!eventType) return "Perubahan uplink";
  return eventType.replaceAll("_", " ");
}

function formatAbsoluteWib(isoTs: string | null | undefined): string {
  if (!isoTs) return "—";
  return `${new Date(isoTs).toLocaleString("id-ID", {
    timeZone: "Asia/Jakarta",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })} WIB`;
}

function formatMetric(metric: number | null | undefined): string {
  return metric == null ? "—" : String(metric);
}

function CheckCard({ title, check }: { title: string; check: WanFailoverHealthCheck }) {
  const state = booleanBadge(check.ok);
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/60 p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">{title}</p>
          <p className="mt-1 text-sm font-semibold text-[var(--color-text)]">{check.iface ?? "—"}</p>
        </div>
        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${state.className}`}>
          {state.label}
        </span>
      </div>
      <dl className="mt-3 grid grid-cols-1 gap-2 text-sm text-[var(--color-text-muted)] sm:grid-cols-2">
        <div>
          <dt className="text-[11px] uppercase tracking-wide">Koneksi</dt>
          <dd className="font-medium text-[var(--color-text)]">{check.connection ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-wide">IPv4</dt>
          <dd className="font-medium text-[var(--color-text)]">{check.ipv4 ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-wide">Gateway</dt>
          <dd className="font-medium text-[var(--color-text)]">{check.gateway ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-[11px] uppercase tracking-wide">Route metric</dt>
          <dd className="font-medium text-[var(--color-text)]">{formatMetric(check.route_metric)}</dd>
        </div>
      </dl>
      <div className="mt-3 rounded-lg border border-dashed border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-text-muted)]">
        <span className="font-medium text-[var(--color-text)]">Health-check:</span> {check.detail ?? "Belum ada detail health-check."}
      </div>
    </div>
  );
}

function Timeline({ items }: { items: WanFailoverEvent[] }) {
  if (items.length === 0) {
    return <EmptyState message="Belum ada perpindahan uplink" detail="Event failover akan tampil di sini saat terjadi perpindahan jalur." />;
  }

  return (
    <ol className="space-y-3">
      {items.map((item, index) => (
        <li key={`${item.ts_utc ?? "event"}-${item.event_type ?? "unknown"}-${index}`} className="relative pl-6">
          <span className="absolute left-0 top-2 h-2.5 w-2.5 rounded-full bg-blue-400" aria-hidden="true" />
          {index < items.length - 1 ? (
            <span className="absolute left-[4px] top-4 h-[calc(100%-0.5rem)] w-px bg-[var(--color-border)]" aria-hidden="true" />
          ) : null}
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/50 px-3 py-2.5">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm font-medium text-[var(--color-text)]">{eventTypeLabel(item.event_type)}</p>
              <p className="text-xs text-[var(--color-text-muted)]">{formatAbsoluteWib(item.ts_utc)}</p>
            </div>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              {item.message ?? uplinkLabel(item.active_uplink_kind, item.active_uplink_iface)}
            </p>
            <p className="mt-1 text-xs text-[var(--color-text-muted)] opacity-80">
              {item.ts_utc ? `Terjadi ${formatRelativeFromIso(item.ts_utc)}` : "Waktu event belum tersedia"}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/60 px-3 py-2.5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-text-muted)]">{label}</p>
      <p className="mt-1 text-sm font-semibold text-[var(--color-text)]">{value}</p>
    </div>
  );
}

function normalizeBadge(status: WanFailoverStatus | null | undefined): WanBadge {
  const badge = status?.primary_badge;
  if (badge === "ethernet-primary" || badge === "wifi-fallback") return badge;
  return "unknown";
}

export function WanFailoverPanel({ status, healthLoading }: WanFailoverPanelProps) {
  const badge = normalizeBadge(status);
  const statusAvailable = !!status?.available;

  return (
    <section className="flex flex-col gap-4">
      <div className="space-y-1">
        <h2 className="text-base font-semibold text-[var(--color-text)] sm:text-lg">Status Jalur Internet</h2>
        <p className="text-sm text-[var(--color-text-muted)]">
          Lihat jalur internet yang sedang dipakai, kondisi Ethernet dan Wi‑Fi, serta riwayat perpindahannya.
        </p>
      </div>

      <Card className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-col gap-2">
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">Status jalur</p>
            {healthLoading ? (
              <div className="h-10 w-40 animate-pulse rounded-2xl bg-[var(--color-border)]" />
            ) : (
              <Badge variant={badge} label={badgeLabel(badge)} />
            )}
          </div>
          <div className="max-w-xl rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/60 px-3 py-2 text-sm text-[var(--color-text-muted)]">
            {healthLoading ? (
              <div className="h-12 w-full animate-pulse rounded bg-[var(--color-border)]" />
            ) : (
              <>
                <p className="font-medium text-[var(--color-text)]">{status?.message ?? "Status jalur internet belum tersedia"}</p>
                <p>{status?.ts_utc ? `Diperbarui ${formatRelativeFromIso(status.ts_utc)}` : "Menunggu status jalur dari perangkat sensor."}</p>
              </>
            )}
          </div>
        </div>

        {healthLoading ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <div key={index} className="h-20 animate-pulse rounded-xl bg-[var(--color-border)]" />
            ))}
          </div>
        ) : statusAvailable ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <SummaryStat label="Jalur aktif" value={uplinkLabel(status?.active_uplink_kind, status?.active_uplink_iface)} />
            <SummaryStat label="Mode" value={modeLabel(status?.mode)} />
            <SummaryStat label="Ethernet" value={booleanBadge(status?.checks.eth.ok).label} />
            <SummaryStat label="Wi‑Fi" value={booleanBadge(status?.checks.wifi.ok).label} />
            <SummaryStat label="Perpindahan terakhir" value={status?.decision.last_change ? formatAbsoluteWib(status.decision.last_change) : "—"} />
          </div>
        ) : (
          <EmptyState message="Status jalur internet belum tersedia" detail="Panel ini akan terisi otomatis saat status jalur sudah masuk dari perangkat sensor." />
        )}

        <details className="group rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/40">
          <summary className="cursor-pointer list-none px-3 py-3 text-sm font-medium text-[var(--color-text)]">
            Detail teknis jaringan
            <span className="ml-2 text-xs font-normal text-[var(--color-text-muted)] group-open:hidden">Buka</span>
            <span className="ml-2 hidden text-xs font-normal text-[var(--color-text-muted)] group-open:inline">Tutup</span>
          </summary>
          <div className="grid gap-3 border-t border-[var(--color-border)] px-3 py-3 lg:grid-cols-2">
            <CheckCard title="Ethernet" check={status?.checks.eth ?? { iface: null, connection: null, ipv4: null, gateway: null, ok: null, detail: null, route_metric: null }} />
            <CheckCard title="Wi‑Fi" check={status?.checks.wifi ?? { iface: null, connection: null, ipv4: null, gateway: null, ok: null, detail: null, route_metric: null }} />
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/60 p-3 lg:col-span-2">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">Rute default</p>
              {status?.default_routes?.length ? (
                <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                  {status.default_routes.map((route, index) => (
                    <div key={`${route.iface ?? "route"}-${route.metric ?? index}-${index}`} className="rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm text-[var(--color-text-muted)]">
                      <p className="font-medium text-[var(--color-text)]">{route.iface ?? "Iface tidak diketahui"}</p>
                      <p>Gateway: {route.gateway ?? "—"}</p>
                      <p>Metric: {formatMetric(route.metric)}</p>
                      <p>Kind: {route.kind ?? "—"}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-[var(--color-text-muted)]">Belum ada data default route.</p>
              )}
            </div>
          </div>
        </details>
      </Card>

      <Card>
        <div className="mb-3 flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">Riwayat perpindahan</p>
          <h3 className="text-base font-semibold text-[var(--color-text)]">Perpindahan jalur terbaru</h3>
          <p className="text-sm text-[var(--color-text-muted)]">Menampilkan riwayat saat koneksi berpindah antara Ethernet dan Wi‑Fi.</p>
        </div>
        {healthLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="h-20 animate-pulse rounded-xl bg-[var(--color-border)]" />
            ))}
          </div>
        ) : (
          <Timeline items={status?.recent_events ?? []} />
        )}
      </Card>
    </section>
  );
}
