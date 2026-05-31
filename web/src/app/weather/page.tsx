"use client";

import { useMemo, useState } from "react";
import { useWeatherHistory } from "@/hooks/useWeatherHistory";
import { NodeSelect } from "@/components/common/NodeSelect";
import {
  TimeRangePicker,
  timeRangeToFromTo,
  type TimeRange,
} from "@/components/common/TimeRangePicker";
import { IntervalSelector } from "@/components/weather/IntervalSelector";
import { TemperatureBandChart } from "@/components/weather/TemperatureBandChart";
import { HumidityPressureChart } from "@/components/weather/HumidityPressureChart";
import { RainChart } from "@/components/weather/RainChart";
import { WindRoseChart } from "@/components/weather/WindRoseChart";
import { WeatherDataTable } from "@/components/weather/WeatherDataTable";
import type { WeatherHistoryParams } from "@/lib/api";

type Interval = WeatherHistoryParams["interval"];

export default function WeatherPage() {
  const [node, setNode] = useState<string>("");
  const [timeRange, setTimeRange] = useState<TimeRange>("24h");
  const [interval, setInterval] = useState<Interval>("1h");

  const nodeParam = node || undefined;
  const { from, to } = useMemo(() => timeRangeToFromTo(timeRange), [timeRange]);

  const { data, isLoading } = useWeatherHistory({
    from,
    to,
    interval,
    node: nodeParam,
  });

  const series = data?.series ?? [];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Riwayat Cuaca</h1>
        <div className="flex flex-wrap items-center gap-3">
          <NodeSelect value={node} onChange={setNode} />
          <IntervalSelector value={interval} onChange={setInterval} />
          <TimeRangePicker value={timeRange} onChange={setTimeRange} />
        </div>
      </div>

      {data?.meta && (
        <p className="text-xs text-[var(--color-text-muted)]">
          {data.meta.count} titik
          {data.meta.downsampled ? " · disampling" : ""}
          {data.node_id ? ` · node ${data.node_id}` : ""}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TemperatureBandChart series={series} loading={isLoading} />
        <HumidityPressureChart series={series} loading={isLoading} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RainChart series={series} loading={isLoading} />
        <WindRoseChart series={series} loading={isLoading} />
      </div>

      <WeatherDataTable series={series} loading={isLoading} />
    </div>
  );
}
