"use client";

import dynamic from "next/dynamic";
import type { HistoryPoint } from "@/lib/types";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";
import { InfoTooltip } from "@/components/common/InfoTooltip";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

const TIMELINE_INFO =
  "Jumlah per menit: Petir = sambaran asli · Gangguan = interferensi buatan manusia · Derau = derau latar tinggi.";

interface ActivityTimelineProps {
  series: HistoryPoint[];
  loading: boolean;
}

export function ActivityTimeline({ series, loading }: ActivityTimelineProps) {
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
          Linimasa Aktivitas
          <InfoTooltip text={TIMELINE_INFO} label="Keterangan linimasa aktivitas" />
        </p>
        <EmptyState
          message="Tidak ada data aktivitas"
          detail="Jumlah akan muncul setelah data petir tersedia."
        />
      </Card>
    );
  }

  const buckets = series.map((p) =>
    new Date(p.bucket as string).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
  );
  const lightning = series.map((p) => (p.lightning_count as number | null) ?? 0);
  const disturber = series.map((p) => (p.disturber_count as number | null) ?? 0);
  const noise = series.map((p) => (p.noise_event_count as number | null) ?? 0);

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
      <p className="mb-2 flex items-center gap-1 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Linimasa Aktivitas
        <InfoTooltip text={TIMELINE_INFO} label="Keterangan linimasa aktivitas" />
      </p>
      <ReactECharts option={option} style={{ height: 200 }} />
    </Card>
  );
}
