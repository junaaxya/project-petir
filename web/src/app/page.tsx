"use client";

import { useState } from "react";
import { useWeatherLatest } from "@/hooks/useLatest";
import { useHealth } from "@/hooks/useHealth";
import { useLightningLatest } from "@/hooks/useLightningLatest";
import { useLatestLightningEvents } from "@/hooks/useLightningEvents";
import { StatusStrip } from "@/components/overview/StatusStrip";
import { DailyForecastSection } from "@/components/overview/DailyForecastSection";
import { OverviewGrid } from "@/components/overview/OverviewGrid";
import { LightningOverviewSection } from "@/components/overview/LightningOverviewSection";
import { NodeSelect } from "@/components/common/NodeSelect";
import { formatRelativeFromIso } from "@/lib/realtime";
import type { NodeStatus } from "@/lib/types";
import { LightningEventsTable } from "@/components/lightning/LightningEventsTable";

function formatWeatherSource(val?: string | null): string {
  if (!val) return "—";
  if (val === "uno_weather") return "Sensor cuaca";
  return val.replaceAll("_", " ");
}

function formatWeatherDevice(val?: string | null): string {
  if (!val) return "—";
  if (val.includes("DFRobot")) return "USB DFRobot";
  if (val.includes("/dev/serial/by-id/")) return val.split("/dev/serial/by-id/")[1] ?? "Serial USB";
  return val;
}

function formatWeatherLatestTs(val?: string | null): string {
  if (!val) return "—";
  return new Date(val).toLocaleString("id-ID", {
    timeZone: "Asia/Jakarta",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }) + " WIB";
}

function getWeatherFreshness(nodeStatus: NodeStatus | null | undefined, isoTs?: string | null) {
  if (nodeStatus === "offline") {
    return {
      label: "Offline",
      detail: isoTs ? `Data terakhir ${formatRelativeFromIso(isoTs)}` : "Data realtime belum tersedia",
      className: "border-red-500/30 bg-red-500/10 text-red-300",
      dotClassName: "bg-red-400",
    };
  }

  if (!isoTs) {
    return {
      label: "Belum ada data",
      detail: "Menunggu data sensor terbaru",
      className: "border-slate-500/30 bg-slate-500/10 text-slate-300",
      dotClassName: "bg-slate-400",
    };
  }

  const ageSec = Math.max(0, Math.floor((Date.now() - new Date(isoTs).getTime()) / 1000));

  if (ageSec <= 20) {
    return {
      label: "Aktif",
      detail: `Data masuk ${formatRelativeFromIso(isoTs)}`,
      className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
      dotClassName: "bg-emerald-400",
    };
  }

  if (ageSec <= 60) {
    return {
      label: "Mulai telat",
      detail: `Data terakhir ${formatRelativeFromIso(isoTs)}`,
      className: "border-amber-500/30 bg-amber-500/10 text-amber-300",
      dotClassName: "bg-amber-400",
    };
  }

  return {
    label: "Terlambat",
    detail: `Data terakhir ${formatRelativeFromIso(isoTs)}`,
    className: "border-orange-500/30 bg-orange-500/10 text-orange-300",
    dotClassName: "bg-orange-400",
  };
}

export default function OverviewPage() {
  const [node, setNode] = useState<string>("");

  const nodeParam = node || undefined;

  const { data: latest, isLoading: latestLoading } = useWeatherLatest(nodeParam);
  const { data: health, isLoading: healthLoading } = useHealth(nodeParam);
  const { data: lightning, isLoading: lightningLoading } = useLightningLatest(nodeParam);
  const { data: latestEvents, isLoading: latestEventsLoading } = useLatestLightningEvents(nodeParam);
  const weatherFreshness = getWeatherFreshness(health?.node_status, latest?.minute?.minute_utc);

  return (
    <div className="flex flex-col gap-5 sm:gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between sm:gap-3">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold text-[var(--color-text)] sm:text-2xl">Ringkasan</h1>
          <p className="max-w-2xl text-sm text-[var(--color-text-muted)]">
            Pantau cuaca dan aktivitas petir dari satu halaman utama. Halaman Petir tetap tersedia saat butuh
            detail lebih lengkap.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:items-end">
          <NodeSelect value={node} onChange={setNode} />
        </div>
      </div>

      <StatusStrip health={health} healthLoading={healthLoading} lightning={lightning} lightningLoading={lightningLoading} />

      <DailyForecastSection node={nodeParam} />

      <LightningOverviewSection lightning={lightning} lightningLoading={lightningLoading} nodeStatus={health?.node_status} />

      <LightningEventsTable
        items={latestEvents?.items ?? []}
        loading={latestEventsLoading}
        pagination={null}
        title="Kejadian Terbaru"
        detail="Event terbaru sensor, tidak dibatasi filter rentang waktu halaman Petir"
      />

      <section className="flex flex-col gap-4">
        <div className="space-y-2">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold text-[var(--color-text)] sm:text-lg">Cuaca Saat Ini</h2>
              <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${weatherFreshness.className}`}>
                <span className={`inline-flex h-2 w-2 rounded-full ${weatherFreshness.dotClassName}`} aria-hidden="true" />
                {weatherFreshness.label}
              </span>
            </div>
            <p className="text-sm text-[var(--color-text-muted)]">
              Data sensor terbaru dari perangkat cuaca. Jika sensor offline, data realtime akan ditandai dengan jelas.
            </p>
          </div>
          {!latestLoading && latest?.minute ? (
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2.5 text-xs text-[var(--color-text-muted)]">
              <div className="flex flex-col gap-1 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-4 sm:gap-y-1">
                <span><span className="font-medium text-[var(--color-text)]">Mode data:</span> Data sensor terbaru</span>
                <span><span className="font-medium text-[var(--color-text)]">Status data:</span> {weatherFreshness.label}</span>
                <span><span className="font-medium text-[var(--color-text)]">Kondisi:</span> {weatherFreshness.detail}</span>
                <span><span className="font-medium text-[var(--color-text)]">Diperbarui:</span> {formatWeatherLatestTs(latest.minute.minute_utc)}</span>
                <span><span className="font-medium text-[var(--color-text)]">Sumber:</span> {formatWeatherSource(latest.minute.source)}</span>
                <span><span className="font-medium text-[var(--color-text)]">Perangkat:</span> {formatWeatherDevice(latest.minute.device)}</span>
              </div>
            </div>
          ) : null}
        </div>
        <OverviewGrid minute={latest?.minute} loading={latestLoading} nodeStatus={health?.node_status} />
      </section>

    </div>
  );
}
