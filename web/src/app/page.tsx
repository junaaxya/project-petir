"use client";

import { useMemo, useState } from "react";
import { useWeatherLatest } from "@/hooks/useLatest";
import { useWeatherHistory } from "@/hooks/useWeatherHistory";
import { useHealth } from "@/hooks/useHealth";
import { useLightningLatest } from "@/hooks/useLightningLatest";
import { StatusStrip } from "@/components/overview/StatusStrip";
import { OverviewGrid } from "@/components/overview/OverviewGrid";
import { TempHumidityChart } from "@/components/overview/TempHumidityChart";
import { NodeSelect } from "@/components/common/NodeSelect";
import {
  TimeRangePicker,
  timeRangeToFromTo,
  type TimeRange,
} from "@/components/common/TimeRangePicker";

export default function OverviewPage() {
  const [node, setNode] = useState<string>("");
  const [timeRange, setTimeRange] = useState<TimeRange>("24h");

  const nodeParam = node || undefined;
  const { from, to } = useMemo(() => timeRangeToFromTo(timeRange), [timeRange]);

  const historyInterval = timeRange === "7d" ? "1h" : timeRange === "24h" ? "1h" : "15m";

  const { data: latest, isLoading: latestLoading } = useWeatherLatest(nodeParam);
  const { data: history, isLoading: historyLoading } = useWeatherHistory({
    from,
    to,
    interval: historyInterval,
    node: nodeParam,
  });
  const { data: health, isLoading: healthLoading } = useHealth(nodeParam);
  const { data: lightning, isLoading: lightningLoading } = useLightningLatest(nodeParam);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-3">
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Ringkasan</h1>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <NodeSelect value={node} onChange={setNode} />
          <TimeRangePicker value={timeRange} onChange={setTimeRange} />
        </div>
      </div>

      <StatusStrip health={health} healthLoading={healthLoading} lightning={lightning} lightningLoading={lightningLoading} />

      <OverviewGrid minute={latest?.minute} loading={latestLoading} />

      <TempHumidityChart series={history?.series ?? []} loading={historyLoading} />
    </div>
  );
}
