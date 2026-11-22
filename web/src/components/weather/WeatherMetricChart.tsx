"use client";

import dynamic from "next/dynamic";
import type { HistoryPoint } from "@/lib/types";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

type Row = HistoryPoint & Record<string, unknown>;

interface WeatherMetricChartProps {
  title: string;
  emptyMessage: string;
  emptyDetail: string;
  unitLabel: string;
  color: string;
  areaColor?: string;
  series: HistoryPoint[];
  buckets: string[];
  loading: boolean;
  getValue: (row: Row) => number | null;
}

export function WeatherMetricChart({
  title,
  emptyMessage,
  emptyDetail,
  unitLabel,
  color,
  areaColor,
  series,
  buckets,
  loading,
  getValue,
}: WeatherMetricChartProps) {
  if (loading) {
    return (
      <Card>
        <div className="h-56 animate-pulse rounded bg-[var(--color-border)]" />
      </Card>
    );
  }

  const rows = series as Row[];
  const values = rows.map((row) => getValue(row));
  const hasAnyValue = values.some((value) => value != null);

  if (series.length === 0 || !hasAnyValue) {
    return (
      <Card>
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          {title}
        </p>
        <EmptyState message={emptyMessage} detail={emptyDetail} />
      </Card>
    );
  }

  const largeDataset = series.length > 500;
  const option = {
    backgroundColor: "transparent",
    animation: !largeDataset,
    grid: { top: 24, right: 8, bottom: 52, left: 8, containLabel: true },
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
    },
    series: [
      {
        name: unitLabel,
        type: "line",
        data: values,
        smooth: !largeDataset,
        symbol: "none",
        sampling: "lttb",
        progressive: 500,
        progressiveThreshold: 500,
        lineStyle: { color, width: 2 },
        areaStyle: areaColor ? { color: areaColor } : undefined,
        connectNulls: false,
      },
    ],
  };

  return (
    <Card>
      <div className="mb-2 flex flex-col gap-1">
        <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">{title}</p>
        <p className="text-xs text-[var(--color-text-muted)]">{unitLabel}</p>
      </div>
      <ReactECharts option={option} style={{ height: "clamp(220px, 58vw, 280px)" }} notMerge />
    </Card>
  );
}
