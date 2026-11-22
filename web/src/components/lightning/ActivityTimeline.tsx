"use client";

import dynamic from "next/dynamic";
import type { HistoryPoint } from "@/lib/types";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";
import { InfoTooltip } from "@/components/common/InfoTooltip";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface ActivityTimelineProps {
  series: HistoryPoint[];
  loading: boolean;
  interval: "1m" | "5m" | "15m" | "1h";
}

export function ActivityTimeline({ series, loading, interval }: ActivityTimelineProps) {
  const intervalLabel = interval === "1h" ? "per jam" : `per ${interval.slice(0, -1)} menit`;
  const title = `Ringkasan Aktivitas ${intervalLabel}`;
  const timelineInfo = `Jumlah ${intervalLabel}: Petir = sambaran asli · Gangguan = interferensi buatan manusia · Derau = derau latar tinggi.`;
  if (loading) {
    return (
      <Card>
        <div className="h-48 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  if (series.length === 0) {
    return (
      <Card>
        <p className="mb-2 flex items-center gap-1 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          {title}
          <InfoTooltip text={timelineInfo} label="Keterangan linimasa aktivitas" />
        </p>
        <EmptyState
          message="Tidak ada data aktivitas"
          detail="Jumlah akan muncul setelah data petir tersedia."
        />
      </Card>
    );
  }

  const buckets = series.map((p) =>
    new Date(p.bucket as string).toLocaleString("id-ID", {
      timeZone: "Asia/Jakarta",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
  );
  const lightning = series.map((p) => (p.lightning_count as number | null) ?? 0);
  const disturber = series.map((p) => (p.disturber_count as number | null) ?? 0);
  const noise = series.map((p) => (p.noise_event_count as number | null) ?? 0);
  const totals = {
    lightning: lightning.reduce((sum, value) => sum + value, 0),
    disturber: disturber.reduce((sum, value) => sum + value, 0),
    noise: noise.reduce((sum, value) => sum + value, 0),
  };
  const activeBuckets = series.filter(
    (_, index) => lightning[index] > 0 || disturber[index] > 0 || noise[index] > 0,
  ).length;

  const option = {
    backgroundColor: "transparent",
    grid: { top: 32, right: 16, bottom: 48, left: 40, containLabel: false },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "#1a1d27",
      borderColor: "#2a2d3a",
      textStyle: { color: "#e2e8f0", fontSize: 12 },
    },
    legend: {
      data: ["Petir", "Gangguan", "Derau"],
      textStyle: { color: "#94a3b8", fontSize: 11 },
      top: 0,
      right: 0,
    },
    xAxis: {
      type: "category",
      data: buckets,
      axisLine: { lineStyle: { color: "#2a2d3a" } },
      axisLabel: { color: "#94a3b8", fontSize: 10, rotate: 30 },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: "#94a3b8", fontSize: 10 },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "#2a2d3a" } },
    },
    series: [
      {
        name: "Petir",
        type: "bar",
        stack: "counts",
        data: lightning,
        itemStyle: { color: "#f59e0b" },
      },
      {
        name: "Gangguan",
        type: "bar",
        stack: "counts",
        data: disturber,
        itemStyle: { color: "#6366f1" },
      },
      {
        name: "Derau",
        type: "bar",
        stack: "counts",
        data: noise,
        itemStyle: { color: "#475569" },
      },
    ],
  };

  return (
    <Card>
      <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="flex items-center gap-1 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          {title}
          <InfoTooltip text={timelineInfo} label="Keterangan linimasa aktivitas" />
        </p>
        <p className="text-xs text-[var(--color-text-muted)]">
          {activeBuckets} interval beraktivitas
        </p>
      </div>
      <div className="mb-3 grid grid-cols-3 gap-2 text-xs">
        <div className="rounded-lg border border-amber-800/60 bg-amber-900/20 px-2 py-1.5">
          <span className="block text-amber-400">Petir</span>
          <strong className="text-sm text-[var(--color-text)]">{totals.lightning}</strong>
        </div>
        <div className="rounded-lg border border-indigo-800/60 bg-indigo-900/20 px-2 py-1.5">
          <span className="block text-indigo-400">Gangguan</span>
          <strong className="text-sm text-[var(--color-text)]">{totals.disturber}</strong>
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-900/30 px-2 py-1.5">
          <span className="block text-slate-400">Derau</span>
          <strong className="text-sm text-[var(--color-text)]">{totals.noise}</strong>
        </div>
      </div>
      <ReactECharts option={option} style={{ height: "clamp(160px, 30vw, 220px)" }} />
    </Card>
  );
}
