"use client";

import dynamic from "next/dynamic";
import type { HistoryPoint } from "@/lib/types";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface HumidityPressureChartProps {
  series: HistoryPoint[];
  loading: boolean;
}

export function HumidityPressureChart({ series, loading }: HumidityPressureChartProps) {
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
          Kelembapan · Tekanan · Cahaya
        </p>
        <EmptyState message="Tidak ada data di rentang ini" detail="Data akan muncul setelah node melakukan sinkronisasi." />
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
  const humids = series.map((p) => (p.humidity_avg as number | null) ?? null);
  const pressures = series.map((p) => (p.pressure_avg as number | null) ?? null);
  const illums = series.map((p) => (p.illuminance_avg as number | null) ?? null);

  const option = {
    backgroundColor: "transparent",
    grid: { top: 32, right: 64, bottom: 40, left: 56, containLabel: false },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1a1d27",
      borderColor: "#2a2d3a",
      textStyle: { color: "#e2e8f0", fontSize: 12 },
    },
    legend: {
      data: ["Kelembapan (%)", "Tekanan (hPa)", "Cahaya (lx)"],
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
    yAxis: [
      {
        type: "value",
        name: "%",
        nameTextStyle: { color: "#94a3b8", fontSize: 10 },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: "#2a2d3a" } },
        min: 0,
        max: 100,
      },
      {
        type: "value",
        name: "hPa",
        nameTextStyle: { color: "#94a3b8", fontSize: 10 },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        axisLine: { show: false },
        splitLine: { show: false },
      },
      {
        type: "value",
        name: "lx",
        nameTextStyle: { color: "#94a3b8", fontSize: 10 },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        axisLine: { show: false },
        splitLine: { show: false },
        position: "right",
        offset: 48,
      },
    ],
    series: [
      {
        name: "Kelembapan (%)",
        type: "line",
        data: humids,
        yAxisIndex: 0,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#38bdf8", width: 2 },
        areaStyle: { color: "rgba(56,189,248,0.06)" },
        connectNulls: false,
      },
      {
        name: "Tekanan (hPa)",
        type: "line",
        data: pressures,
        yAxisIndex: 1,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#a78bfa", width: 2 },
        connectNulls: false,
      },
      {
        name: "Cahaya (lx)",
        type: "line",
        data: illums,
        yAxisIndex: 2,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#fbbf24", width: 1.5, type: "dashed" },
        connectNulls: false,
      },
    ],
  };

  return (
    <Card>
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Kelembapan · Tekanan · Cahaya
      </p>
      <ReactECharts option={option} style={{ height: 220 }} notMerge />
    </Card>
  );
}
