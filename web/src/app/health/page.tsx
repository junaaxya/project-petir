"use client";

import { Suspense, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useHealth, useHealthDiagnostics } from "@/hooks/useHealth";
import { useSystemEvents } from "@/hooks/useSystemEvents";
import { useIngestRuns } from "@/hooks/useIngestRuns";
import { NodeSelect } from "@/components/common/NodeSelect";
import { Badge } from "@/components/common/Badge";
import { HistoryFilterBar } from "@/components/common/HistoryFilterBar";
import { FreshnessTable } from "@/components/health/FreshnessTable";
import { SystemEventsList } from "@/components/health/SystemEventsList";
import { BatchSuccessRate } from "@/components/health/BatchSuccessRate";
import { WanFailoverPanel } from "@/components/overview/WanFailoverPanel";
import { Card } from "@/components/common/Card";
import { DataFreshnessNotice, QueryErrorState } from "@/components/common/QueryState";
import {
  dateRangeToApiRange,
  normalizeDateRange,
  parseHistoryRangePreset,
  parsePositiveInt,
  presetToDateRange,
  type HistoryRangePreset,
} from "@/lib/historyFilters";
import { nodeStatusLabel } from "@/lib/uiLabels";

const ACTIVITY_TYPE_OPTIONS = [
  { value: "all", label: "Semua" },
  { value: "heartbeat", label: "Heartbeat" },
  { value: "status", label: "Status" },
  { value: "other", label: "Lainnya" },
] as const;

function parseActivityType(value: string | null): "all" | "heartbeat" | "status" | "other" {
  if (value === "heartbeat" || value === "status" || value === "other") return value;
  return "all";
}

function HealthPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const node = searchParams.get("node") ?? "";
  const operatorMode = searchParams.get("operator") === "1";
  const rangePreset = parseHistoryRangePreset(searchParams.get("range"));
  const statusPage = parsePositiveInt(searchParams.get("status_page"), 1);
  const technicalPage = parsePositiveInt(searchParams.get("technical_page"), 1);
  const activityPage = parsePositiveInt(searchParams.get("activity_page"), 1);
  const activityType = parseActivityType(searchParams.get("activity_type"));

  const { fromDate, toDate } = useMemo(() => {
    if (rangePreset === "custom") {
      return normalizeDateRange(
        searchParams.get("from_date") ?? "",
        searchParams.get("to_date") ?? "",
      );
    }
    return presetToDateRange(rangePreset);
  }, [rangePreset, searchParams]);

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
      setQuery({
        range: "custom",
        from_date: fromDate,
        to_date: toDate,
        status_page: "1",
        technical_page: "1",
        activity_page: "1",
      });
      return;
    }
    setQuery({
      range: preset,
      from_date: null,
      to_date: null,
      status_page: "1",
      technical_page: "1",
      activity_page: "1",
    });
  };

  const nodeParam = node || undefined;

  const healthQuery = useHealth(nodeParam);
  const diagnosticsQuery = useHealthDiagnostics(nodeParam, operatorMode);
  const statusQuery = useSystemEvents({
    from,
    to,
    node: nodeParam,
    scope: "status_changes",
    page: statusPage,
    page_size: 20,
  }, operatorMode);
  const technicalQuery = useSystemEvents({
    from,
    to,
    node: nodeParam,
    scope: "technical_issues",
    page: technicalPage,
    page_size: 20,
  }, operatorMode);
  const activityQuery = useSystemEvents({
    from,
    to,
    node: nodeParam,
    scope: "all",
    event_group: activityType,
    page: activityPage,
    page_size: 20,
  }, operatorMode);
  const ingestQuery = useIngestRuns(nodeParam, operatorMode);
  const health = healthQuery.data;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-3">
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Kesehatan</h1>
        {operatorMode ? (
          <NodeSelect
            value={node}
            onChange={(value) =>
              setQuery({ node: value || null, status_page: "1", technical_page: "1", activity_page: "1" })
            }
          />
        ) : null}
      </div>

      {operatorMode ? (
        <HistoryFilterBar
        preset={rangePreset}
        fromDate={fromDate}
        toDate={toDate}
        onPresetChange={handlePresetChange}
        onFromDateChange={(value) =>
          setQuery({
            range: "custom",
            from_date: value,
            to_date: toDate,
            status_page: "1",
            technical_page: "1",
            activity_page: "1",
          })
        }
        onToDateChange={(value) =>
          setQuery({
            range: "custom",
            from_date: fromDate,
            to_date: value,
            status_page: "1",
            technical_page: "1",
            activity_page: "1",
          })
        }
      />
      ) : null}

      {healthQuery.isError ? (
        <QueryErrorState error={healthQuery.error} onRetry={() => healthQuery.refetch()} label="Status publik" />
      ) : (
        <>
          <Card className="flex flex-wrap items-center gap-6">
            <div className="flex flex-col gap-1">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                Status Stasiun
              </p>
              {healthQuery.isLoading ? (
                <div className="h-6 w-20 animate-pulse rounded-full bg-[var(--color-border)]" />
              ) : (
                <Badge
                  variant={health?.station_status ?? "no_data"}
                  label={nodeStatusLabel(health?.station_status)}
                />
              )}
            </div>
            <div className="flex flex-col gap-1">
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                Ketersediaan Data
              </p>
              {healthQuery.isLoading ? (
                <div className="h-6 w-24 animate-pulse rounded bg-[var(--color-border)]" />
              ) : (
                <span className="text-sm font-medium text-[var(--color-text)]">
                  {health?.data_availability === "available"
                    ? "Tersedia"
                    : health?.data_availability === "degraded"
                      ? "Terbatas"
                      : "Tidak tersedia"}
                </span>
              )}
            </div>
          </Card>
          <DataFreshnessNotice
            updatedAtUtc={health?.updated_at_utc}
            isStale={health?.data_availability !== "available"}
            isFetching={healthQuery.isFetching}
          />
          <FreshnessTable streams={health?.freshness ?? []} loading={healthQuery.isLoading} />
        </>
      )}

      <Card className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[var(--color-text)]">Panel operator terlindungi</h2>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Diagnostik jaringan, proses ingest, dan log internal hanya dimuat saat panel ini dibuka.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setQuery({ operator: operatorMode ? null : "1" })}
          className="rounded-md border border-[var(--color-border)] px-3 py-2 text-sm font-medium text-[var(--color-text)] hover:bg-[var(--color-surface-muted)]"
        >
          {operatorMode ? "Sembunyikan panel operator" : "Buka panel operator"}
        </button>
      </Card>

      {operatorMode ? (
        <>
      {diagnosticsQuery.isError ? (
        <QueryErrorState
          error={diagnosticsQuery.error}
          onRetry={() => diagnosticsQuery.refetch()}
          label="Diagnostik operator"
        />
      ) : (
        <WanFailoverPanel
          status={diagnosticsQuery.data?.wan_failover}
          healthLoading={diagnosticsQuery.isLoading}
        />
      )}

      {ingestQuery.isError ? (
        <QueryErrorState error={ingestQuery.error} onRetry={() => ingestQuery.refetch()} label="Proses ingest" />
      ) : (
        <BatchSuccessRate runs={ingestQuery.data?.items ?? []} loading={ingestQuery.isLoading} />
      )}

      {statusQuery.isError ? (
        <QueryErrorState error={statusQuery.error} onRetry={() => statusQuery.refetch()} label="Riwayat status sensor" />
      ) : (
        <SystemEventsList
          items={statusQuery.data?.items ?? []}
          loading={statusQuery.isLoading}
          pagination={statusQuery.data?.meta ?? null}
          onPageChange={(page) => setQuery({ status_page: String(page) })}
          title="Riwayat Status Sensor"
          description="Menampilkan riwayat saat sensor atau Raspberry Pi terdeteksi offline lalu online kembali. Ini dipisah agar perubahan status lebih mudah dilihat."
          emptyMessage="Belum ada perubahan status sensor"
          emptyDetail="Saat ada sensor mati atau kembali aktif, riwayatnya akan muncul di sini."
          aggregateWarnings={false}
        />
      )}

      {technicalQuery.isError ? (
        <QueryErrorState error={technicalQuery.error} onRetry={() => technicalQuery.refetch()} label="Log gangguan teknis" />
      ) : (
        <SystemEventsList
          items={technicalQuery.data?.items ?? []}
          loading={technicalQuery.isLoading}
          pagination={technicalQuery.data?.meta ?? null}
          onPageChange={(page) => setQuery({ technical_page: String(page) })}
          title="Log Gangguan Teknis"
          description="Menampilkan warning, error, dan gangguan teknis penting. Warning petir yang berulang diringkas agar tidak menutupi riwayat status sensor."
          emptyMessage="Tidak ada gangguan teknis terbaru"
          emptyDetail="Jika ada warning atau error penting dari ingest/server, riwayatnya akan muncul di sini."
          aggregateWarnings
        />
      )}

      {activityQuery.isError ? (
        <QueryErrorState error={activityQuery.error} onRetry={() => activityQuery.refetch()} label="Aktivitas sistem" />
      ) : (
        <SystemEventsList
          items={activityQuery.data?.items ?? []}
          loading={activityQuery.isLoading}
          pagination={activityQuery.data?.meta ?? null}
          onPageChange={(page) => setQuery({ activity_page: String(page) })}
          title="Aktivitas Sistem"
          description="Menampilkan aktivitas sistem pada rentang waktu yang dipilih. Heartbeat rutin diringkas per sumber agar lebih mudah dipantau."
          emptyMessage="Belum ada aktivitas sistem"
          emptyDetail="Jika ada heartbeat, info status, atau log sistem lainnya, riwayatnya akan muncul di sini."
          aggregateWarnings={false}
          aggregateRoutineInfo
          filterOptions={[...ACTIVITY_TYPE_OPTIONS]}
          activeFilter={activityType}
          onFilterChange={(value) => setQuery({ activity_type: value, activity_page: "1" })}
        />
      )}
        </>
      ) : null}
    </div>
  );
}

export default function HealthPage() {
  return (
    <Suspense fallback={<div className="h-24 animate-pulse rounded bg-[var(--color-border)]" />}>
      <HealthPageContent />
    </Suspense>
  );
}
