"use client";

import dynamic from "next/dynamic";
import type { HistoryPoint } from "@/lib/types";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface RainChartProps {
  series: HistoryPoint[];
  loading: boolean;
}

export function RainChart({ series, loading }: RainChartProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-40 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const hasRain = series.some((p) => (p.rain_max as number | null) != null);

  if (series.length === 0 || !hasRain) {
    return (
      <Card>
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Hujan
        </p>
        <EmptyState message="Tidak ada data hujan" detail="Data sensor hujan akan muncul di sini." />
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
  const rains = series.map((p) => (p.rain_max as number | null) ?? 0);

  const option = {
    backgroundColor: "transparent",
    grid: { top: 18, right: 8, bottom: 52, left: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1a1d27",
      borderColor: "#2a2d3a",
      textStyle: { color: "#e2e8f0", fontSize: 12 },
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
      min: 0,
    },
    series: [
      {
        name: "Hujan (mm)",
        type: "bar",
        data: rains,
        itemStyle: { color: "#38bdf8", borderRadius: [2, 2, 0, 0] },
        barMaxWidth: 12,
      },
    ],
  };

  return (
    <Card>
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Hujan
      </p>
      <ReactECharts option={option} style={{ height: "clamp(200px, 54vw, 250px)" }} notMerge />
    </Card>
  );
}
