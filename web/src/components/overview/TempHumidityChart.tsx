"use client";

import dynamic from "next/dynamic";
import type { HistoryPoint } from "@/lib/types";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface TempHumidityChartProps {
  series: HistoryPoint[];
  loading: boolean;
}

export function TempHumidityChart({ series, loading }: TempHumidityChartProps) {
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
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Suhu &amp; Kelembapan — 24 jam
        </p>
        <EmptyState message="Tidak ada data di rentang ini" detail="Data akan muncul setelah node melakukan sinkronisasi." />
      </Card>
    );
  }

  const buckets = series.map((p) =>
    new Date(p.bucket as string).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  );
  const temps = series.map((p) => (p.temperature_avg as number | null) ?? null);
  const humids = series.map((p) => (p.humidity_avg as number | null) ?? null);

  const option = {
    backgroundColor: "transparent",
    grid: { top: 24, right: 48, bottom: 32, left: 48, containLabel: false },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1a1d27",
      borderColor: "#2a2d3a",
      textStyle: { color: "#e2e8f0", fontSize: 12 },
    },
    legend: {
      data: ["Suhu (°C)", "Kelembapan (%)"],
      textStyle: { color: "#94a3b8", fontSize: 11 },
      top: 0,
      right: 0,
    },
    xAxis: {
      type: "category",
      data: buckets,
      axisLine: { lineStyle: { color: "#2a2d3a" } },
      axisLabel: { color: "#94a3b8", fontSize: 10 },
      splitLine: { show: false },
    },
    yAxis: [
      {
        type: "value",
        name: "°C",
        nameTextStyle: { color: "#94a3b8", fontSize: 10 },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: "#2a2d3a" } },
      },
      {
        type: "value",
        name: "%",
        nameTextStyle: { color: "#94a3b8", fontSize: 10 },
        axisLabel: { color: "#94a3b8", fontSize: 10 },
        axisLine: { show: false },
        splitLine: { show: false },
        min: 0,
        max: 100,
      },
    ],
    series: [
      {
        name: "Suhu (°C)",
        type: "line",
        data: temps,
        yAxisIndex: 0,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#f97316", width: 2 },
        areaStyle: { color: "rgba(249,115,22,0.08)" },
        connectNulls: false,
      },
      {
        name: "Kelembapan (%)",
        type: "line",
        data: humids,
        yAxisIndex: 1,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#38bdf8", width: 2 },
        areaStyle: { color: "rgba(56,189,248,0.06)" },
        connectNulls: false,
      },
    ],
  };

  return (
    <Card>
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Suhu &amp; Kelembapan — 24 jam
      </p>
      <ReactECharts option={option} style={{ height: 200 }} notMerge />
    </Card>
  );
}
