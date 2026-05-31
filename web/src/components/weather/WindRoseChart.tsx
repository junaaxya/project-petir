"use client";

import dynamic from "next/dynamic";
import type { HistoryPoint } from "@/lib/types";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

const DIR_LABELS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

function buildWindRoseData(series: HistoryPoint[]): number[] {
  const counts = new Array<number>(8).fill(0);
  for (const p of series) {
    const deg = p.latest_wind_dir_deg as number | null;
    const speed = p.wind_speed_avg as number | null;
    if (deg == null || speed == null || speed === 0) continue;
    const idx = Math.round(((deg % 360) + 360) % 360 / 45) % 8;
    counts[idx]++;
  }
  return counts;
}

interface WindRoseChartProps {
  series: HistoryPoint[];
  loading: boolean;
}

export function WindRoseChart({ series, loading }: WindRoseChartProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-56 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const hasWind = series.some(
    (p) => (p.wind_speed_avg as number | null) != null && (p.wind_speed_avg as number) > 0,
  );

  if (series.length === 0 || !hasWind) {
    return (
      <Card>
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Arah Angin
        </p>
        <EmptyState
          message="Tidak ada angin di rentang ini"
          detail="Semua pembacaan tenang (tidak ada angin terukur)."
        />
      </Card>
    );
  }

  const counts = buildWindRoseData(series);

  const option = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "#1a1d27",
      borderColor: "#2a2d3a",
      textStyle: { color: "#e2e8f0", fontSize: 12 },
        formatter: (params: { name: string; value: number }) =>
        `${params.name}: ${params.value} pembacaan`,
    },
    polar: { radius: "70%" },
    angleAxis: {
      type: "category",
      data: DIR_LABELS,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "#2a2d3a" } },
      axisLabel: { color: "#94a3b8", fontSize: 11 },
      splitLine: { lineStyle: { color: "#2a2d3a" } },
    },
    radiusAxis: {
      axisLabel: { color: "#94a3b8", fontSize: 9 },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "#2a2d3a" } },
    },
    series: [
      {
        name: "Arah Angin",
        type: "bar",
        data: counts,
        coordinateSystem: "polar",
        itemStyle: { color: "#38bdf8", opacity: 0.85 },
        barMaxWidth: 20,
      },
    ],
  };

  return (
    <Card>
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
        Arah Angin
      </p>
      <ReactECharts option={option} style={{ height: 220 }} notMerge />
    </Card>
  );
}
