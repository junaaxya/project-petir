"use client";

import dynamic from "next/dynamic";
import type { HistoryPoint } from "@/lib/types";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface TemperatureBandChartProps {
  series: HistoryPoint[];
  loading: boolean;
}

export function TemperatureBandChart({ series, loading }: TemperatureBandChartProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-56 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  if (series.length === 0) {
    return (
      <Card>
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Pita Suhu
        </p>
        <EmptyState message="Tidak ada data suhu" detail="Data akan muncul setelah node melakukan sinkronisasi." />
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
  const mins = series.map((p) => (p.temperature_min as number | null) ?? null);
  const maxs = series.map((p) => (p.temperature_max as number | null) ?? null);
  const avgs = series.map((p) => (p.temperature_avg as number | null) ?? null);

  const option = {
    backgroundColor: "transparent",
    grid: { top: 56, right: 8, bottom: 52, left: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1a1d27",
      borderColor: "#2a2d3a",
      textStyle: { color: "#e2e8f0", fontSize: 12 },
    },
    legend: {
      type: "scroll",
      orient: "horizontal",
      data: ["Min", "Maks", "Rata²"],
      textStyle: { color: "#94a3b8", fontSize: 10 },
      top: 0,
      left: 0,
      right: 0,
      itemWidth: 10,
      itemHeight: 6,
    },
    xAxis: {
      type: "category",
      data: buckets,
      axisLine: { lineStyle: { color: "#2a2d3a" } },
      axisLabel: { color: "#94a3b8", fontSize: 10, rotate: 35, hideOverlap: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      name: "",
      nameTextStyle: { color: "#94a3b8", fontSize: 10 },
      axisLabel: { color: "#94a3b8", fontSize: 9 },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "#2a2d3a" } },
    },
    series: [
      {
        name: "Min",
        type: "line",
        data: mins,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#38bdf8", width: 1, type: "dashed" },
        areaStyle: { color: "rgba(56,189,248,0.06)" },
        connectNulls: false,
      },
      {
        name: "Maks",
        type: "line",
        data: maxs,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#f97316", width: 1, type: "dashed" },
        areaStyle: { color: "rgba(249,115,22,0.06)" },
        connectNulls: false,
      },
      {
        name: "Rata²",
        type: "line",
        data: avgs,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#facc15", width: 2 },
        connectNulls: false,
      },
    ],
  };

  return (
    <Card>
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Pita Suhu
      </p>
      <ReactECharts option={option} style={{ height: "clamp(210px, 56vw, 270px)" }} notMerge />
    </Card>
  );
}
