"use client";

import { useMemo, useState } from "react";
import { useLightningLatest } from "@/hooks/useLightningLatest";
import { useLightningHistory } from "@/hooks/useLightningHistory";
import { useLightningEvents } from "@/hooks/useLightningEvents";
import { NodeSelect } from "@/components/common/NodeSelect";
import {
  TimeRangePicker,
  timeRangeToFromTo,
  type TimeRange,
} from "@/components/common/TimeRangePicker";
import { LightningStatusBadge } from "@/components/lightning/LightningStatusBadge";
import { LastEventCard } from "@/components/lightning/LastEventCard";
import { ActivityTimeline } from "@/components/lightning/ActivityTimeline";
import { LightningEventsTable } from "@/components/lightning/LightningEventsTable";
import { StrikeSummaryTable } from "@/components/lightning/StrikeSummaryTable";
import { EmptyState } from "@/components/common/EmptyState";
import { Card } from "@/components/common/Card";
import { InfoTooltip } from "@/components/common/InfoTooltip";
import { EVENT_TYPE_INFO, LIGHTNING_STATUS_INFO } from "@/components/lightning/lightningTerms";

export default function LightningPage() {
  const [node, setNode] = useState<string>("");
  const [timeRange, setTimeRange] = useState<TimeRange>("6h");

  const nodeParam = node || undefined;
  const { from, to } = useMemo(() => timeRangeToFromTo(timeRange), [timeRange]);

  const { data: latest, isLoading: latestLoading } = useLightningLatest(nodeParam);
  const { data: history, isLoading: historyLoading } = useLightningHistory({
    from,
    to,
    interval: "1m",
    node: nodeParam,
  });
  const { data: events, isLoading: eventsLoading } = useLightningEvents({
    from,
    to,
    node: nodeParam,
    limit: 100,
  });

  const status = latest?.minute?.status ?? null;
  const series = history?.series ?? [];
  const items = events?.items ?? [];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-3">
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Petir</h1>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <NodeSelect value={node} onChange={setNode} />
          <TimeRangePicker value={timeRange} onChange={setTimeRange} />
        </div>
      </div>

      <Card className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            Status Saat Ini
          </p>
          {latestLoading ? (
            <div className="h-9 w-28 animate-pulse rounded-2xl bg-[var(--color-border)]" />
          ) : (
            <div className="flex items-center gap-2">
              <LightningStatusBadge status={status} large />
              <InfoTooltip
                text={LIGHTNING_STATUS_INFO[status ?? "no_data"]}
                label={`Keterangan status: ${status ?? "no_data"}`}
              />
            </div>
          )}
        </div>
        {latest?.minute && (
          <div className="flex flex-col gap-0.5 text-right">
            <span className="text-xs text-[var(--color-text-muted)]">
              {latest.node_id ? `Node: ${latest.node_id}` : ""}
            </span>
            <span className="text-xs text-[var(--color-text-muted)]">
              {latest.minute.minute_utc
                ? `Diperbarui: ${new Date(latest.minute.minute_utc).toLocaleString([], { hour: "2-digit", minute: "2-digit" })}`
                : ""}
            </span>
          </div>
        )}
      </Card>

      {!latestLoading && latest?.minute == null && (
        <Card>
          <EmptyState
            message="Tidak ada data petir"
            detail="Sensor ini melaporkan data yang jarang. Status di atas mencerminkan kondisi terkini yang diketahui."
          />
        </Card>
      )}

      <Card>
        <p className="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Keterangan Istilah
        </p>
        <div className="flex flex-col gap-2 sm:flex-row sm:gap-6">
          <div className="flex items-start gap-2">
            <span className="mt-0.5 shrink-0 text-xs font-semibold text-amber-400">Petir</span>
            <span className="text-xs text-[var(--color-text-muted)]">{EVENT_TYPE_INFO.lightning}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="mt-0.5 shrink-0 text-xs font-semibold text-indigo-400">Gangguan</span>
            <span className="text-xs text-[var(--color-text-muted)]">{EVENT_TYPE_INFO.disturber}</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="mt-0.5 shrink-0 text-xs font-semibold text-slate-400">Derau</span>
            <span className="text-xs text-[var(--color-text-muted)]">{EVENT_TYPE_INFO.noise}</span>
          </div>
        </div>
      </Card>

      <LastEventCard minute={latest?.minute ?? null} loading={latestLoading} />

      <ActivityTimeline series={series} loading={historyLoading} />

      <StrikeSummaryTable items={items} loading={eventsLoading} />

      <LightningEventsTable items={items} loading={eventsLoading} />
    </div>
  );
}
