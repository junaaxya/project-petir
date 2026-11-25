"use client";

import { Suspense, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useHealth } from "@/hooks/useHealth";
import { useLightningLatest } from "@/hooks/useLightningLatest";
import { useLightningHistory } from "@/hooks/useLightningHistory";
import { useLightningEvents } from "@/hooks/useLightningEvents";
import { NodeSelect } from "@/components/common/NodeSelect";
import { HistoryFilterBar } from "@/components/common/HistoryFilterBar";
import { LightningStatusBadge } from "@/components/lightning/LightningStatusBadge";
import { LastEventCard } from "@/components/lightning/LastEventCard";
import { ActivityTimeline } from "@/components/lightning/ActivityTimeline";
import { LightningEventsTable } from "@/components/lightning/LightningEventsTable";
import { EmptyState } from "@/components/common/EmptyState";
import { QueryErrorState } from "@/components/common/QueryState";
import { Card } from "@/components/common/Card";
import { InfoTooltip } from "@/components/common/InfoTooltip";
import { EVENT_TYPE_INFO, LIGHTNING_STATUS_INFO } from "@/components/lightning/lightningTerms";
import { Badge } from "@/components/common/Badge";
import {
  dateRangeToApiRange,
  normalizeDateRange,
  parseHistoryRangePreset,
  parsePositiveInt,
  presetToDateRange,
  type HistoryRangePreset,
} from "@/lib/historyFilters";
import { isRealtimeUnavailable, realtimeSnapshotDetail } from "@/lib/realtime";
import { lightningStatusLabel, nodeStatusLabel } from "@/lib/uiLabels";
import { exportLightningEvents } from "@/lib/api";

function LightningPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const node = searchParams.get("node") ?? "";
  const rangePreset = parseHistoryRangePreset(searchParams.get("range"));
  const page = parsePositiveInt(searchParams.get("page"), 1);

  const { fromDate, toDate } = useMemo(() => {
    if (rangePreset === "custom") {
      return normalizeDateRange(
        searchParams.get("from_date") ?? "",
        searchParams.get("to_date") ?? "",
      );
    }
    return presetToDateRange(rangePreset);
  }, [rangePreset, searchParams]);

  const nodeParam = node || undefined;
  const { from, to } = useMemo(() => dateRangeToApiRange(fromDate, toDate), [fromDate, toDate]);

  const setQuery = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value == null || value === "") next.delete(key);
      else next.set(key, value);
    }
    const qs = next.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };

  const handlePresetChange = (preset: HistoryRangePreset) => {
    if (preset === "custom") {
      setQuery({ range: "custom", from_date: fromDate, to_date: toDate, page: "1" });
      return;
    }
    setQuery({ range: preset, from_date: null, to_date: null, page: "1" });
  };

  const rangeDays = useMemo(() => {
    const start = new Date(`${fromDate}T00:00:00`).getTime();
    const end = new Date(`${toDate}T00:00:00`).getTime();
    return Math.max(1, Math.floor((end - start) / 86_400_000) + 1);
  }, [fromDate, toDate]);

  const historyInterval =
    rangeDays <= 1 ? "1m" : rangeDays <= 7 ? "15m" : "1h";

  const healthQuery = useHealth(nodeParam);
  const latestQuery = useLightningLatest(nodeParam);
  const historyQuery = useLightningHistory({
    from,
    to,
    interval: historyInterval,
    node: nodeParam,
  });
  const eventsQuery = useLightningEvents({
    from,
    to,
    node: nodeParam,
    page,
    page_size: 20,
  });
  const { data: health, isLoading: healthLoading } = healthQuery;
  const { data: latest, isLoading: latestLoading } = latestQuery;
  const { data: history, isLoading: historyLoading } = historyQuery;
  const { data: events, isLoading: eventsLoading } = eventsQuery;


  const status = latest?.minute?.status ?? null;
  const realtimeUnavailable = isRealtimeUnavailable(health?.station_status);
  const snapshotDetail = realtimeSnapshotDetail(health?.station_status, latest?.minute?.minute_utc);
  const series = history?.series ?? [];
  const items = events?.items ?? [];


  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-3">
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Petir</h1>
        <NodeSelect value={node} onChange={(value) => setQuery({ node: value || null, page: "1" })} />
      </div>

      <HistoryFilterBar
        preset={rangePreset}
        fromDate={fromDate}
        toDate={toDate}
        onPresetChange={handlePresetChange}
        onFromDateChange={(value) =>
          setQuery({ range: "custom", from_date: value, to_date: toDate, page: "1" })
        }
        onToDateChange={(value) =>
          setQuery({ range: "custom", from_date: fromDate, to_date: value, page: "1" })
        }
      />

      {healthQuery.isError && (
        <QueryErrorState error={healthQuery.error} onRetry={() => healthQuery.refetch()} label="Status stasiun" />
      )}
      {latestQuery.isError && (
        <QueryErrorState error={latestQuery.error} onRetry={() => latestQuery.refetch()} label="Status petir" />
      )}

      <div className={healthQuery.isError || latestQuery.isError ? "hidden" : "contents"}>
      <Card className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            Status Saat Ini
          </p>
          {latestLoading || healthLoading ? (
            <div className="h-9 w-28 animate-pulse rounded-2xl bg-[var(--color-border)]" />
          ) : (
            <div className="flex items-center gap-2">
              {realtimeUnavailable ? (
                <Badge variant="offline" label="Offline" />
              ) : (
                <LightningStatusBadge status={status} large />
              )}
              <InfoTooltip
                text={realtimeUnavailable
                  ? "Sensor sedang offline. Status petir realtime tidak tersedia; dashboard menampilkan snapshot terakhir yang tersimpan."
                  : LIGHTNING_STATUS_INFO[status ?? "no_data"]}
                label={`Keterangan status: ${realtimeUnavailable ? nodeStatusLabel("offline") : lightningStatusLabel(status)}`}
              />
            </div>
          )}
        </div>
        {latest?.minute && (
          <div className="flex flex-col gap-0.5 text-right">
            <span className="text-xs text-[var(--color-text-muted)]">
              {latest.node_id ? `Lokasi sensor: ${latest.node_id}` : ""}
            </span>
            <span className="text-xs text-[var(--color-text-muted)]">
              {realtimeUnavailable
                ? (snapshotDetail ?? "Data terakhir tersedia")
                : latest.minute.minute_utc
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

      <LastEventCard
        minute={latest?.minute ?? null}
        loading={latestLoading || healthLoading}
        offlineDetail={realtimeUnavailable ? snapshotDetail : undefined}
      />
      </div>

      {historyQuery.isError ? (
        <QueryErrorState error={historyQuery.error} onRetry={() => historyQuery.refetch()} label="Riwayat petir" />
      ) : (
        <ActivityTimeline series={series} loading={historyLoading} interval={historyInterval} />
      )}

      {eventsQuery.isError ? (
        <QueryErrorState error={eventsQuery.error} onRetry={() => eventsQuery.refetch()} label="Rekaman petir" />
      ) : (
      <LightningEventsTable
        items={items}
        loading={eventsLoading}
        pagination={events?.meta ?? null}
        onPageChange={(nextPage) => setQuery({ page: String(nextPage) })}
        onExport={async () => {
          const result = await exportLightningEvents({ from, to, node: nodeParam });
          return result.items;
        }}
        title="Rekaman Event Sensor"
        detail="Grafik aktivitas memakai ringkasan per menit; daftar ini menampilkan rekaman individual sensor pada halaman saat ini."
      />
      )}

    </div>
  );
}

export default function LightningPage() {
  return (
    <Suspense fallback={<div className="h-24 animate-pulse rounded bg-[var(--color-border)]" />}>
      <LightningPageContent />
    </Suspense>
  );
}
