"use client";

import { useMemo, useState } from "react";
import { useQualityEvents } from "@/hooks/useQualityEvents";
import { NodeSelect } from "@/components/common/NodeSelect";
import {
  TimeRangePicker,
  timeRangeToFromTo,
  type TimeRange,
} from "@/components/common/TimeRangePicker";
import { QualityEventsTable } from "@/components/quality/QualityEventsTable";
import { QualityDistribution } from "@/components/quality/QualityDistribution";
import { ReasonCodesBreakdown } from "@/components/quality/ReasonCodesBreakdown";

export default function QualityPage() {
  const [node, setNode] = useState<string>("");
  const [timeRange, setTimeRange] = useState<TimeRange>("24h");

  const nodeParam = node || undefined;
  const { from, to } = useMemo(() => timeRangeToFromTo(timeRange), [timeRange]);

  const { data, isLoading } = useQualityEvents({
    from,
    to,
    node: nodeParam,
    limit: 200,
  });

  const items = data?.items ?? [];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-3">
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Kualitas Data</h1>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <NodeSelect value={node} onChange={setNode} />
          <TimeRangePicker value={timeRange} onChange={setTimeRange} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <QualityDistribution items={items} loading={isLoading} />
        <ReasonCodesBreakdown items={items} loading={isLoading} />
      </div>

      <QualityEventsTable items={items} loading={isLoading} />
    </div>
  );
}
