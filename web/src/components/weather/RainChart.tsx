"use client";

import dynamic from "next/dynamic";
import type { HistoryPoint } from "@/lib/types";
import { getRain } from "@/lib/chart-fields";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";
import { useSiteConfig } from "@/components/common/SiteConfigProvider";
import { rainChartSubtitle, rainSeriesLabel } from "@/lib/rainSemantics";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface RainChartProps {
  series: HistoryPoint[];
  buckets: string[];
  loading: boolean;
}

export function RainChart({ series, buckets, loading }: RainChartProps) {
  const { rainSemantics } = useSiteConfig();
  const raw = series.length > 0 && "rain_mm" in series[0];
  const subtitle = rainChartSubtitle(rainSemantics, raw);
  if (loading) {
    return (
      <Card>
        <div className="h-40 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const hasRain = series.some((p) => getRain(p as HistoryPoint & Record<string, unknown>) != null);

  if (series.length === 0 || !hasRain) {
    return (
      <Card>
        <div className="mb-2 flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">Curah Hujan</p>
          <p className="text-xs text-[var(--color-text-muted)]">{subtitle}</p>
        </div>
        <EmptyState message="Tidak ada data hujan" detail="Data curah hujan akan muncul setelah sensor kembali sinkron." />
      </Card>
    );
  }

  const rains = series.map((p) => getRain(p as HistoryPoint & Record<string, unknown>) ?? 0);
  const largeDataset = series.length > 500;

  const option = {
    backgroundColor: "transparent",
    animation: !largeDataset,
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
        name: rainSeriesLabel(rainSemantics, raw),
        type: "bar",
        data: rains,
        large: largeDataset,
        largeThreshold: 500,
        progressive: 500,
        progressiveThreshold: 500,
        itemStyle: { color: "#38bdf8", borderRadius: [2, 2, 0, 0] },
        barMaxWidth: 12,
      },
    ],
  };

  return (
    <Card>
      <div className="mb-2 flex flex-col gap-1">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">Curah Hujan</p>
        <p className="text-xs text-[var(--color-text-muted)]">{subtitle}</p>
      </div>
      <ReactECharts option={option} style={{ height: "clamp(200px, 54vw, 250px)" }} notMerge />
    </Card>
  );
}
