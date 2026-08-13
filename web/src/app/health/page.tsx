"use client";

import { Suspense, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useHealth } from "@/hooks/useHealth";
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

function fmtLag(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h`;
}

function HealthPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const node = searchParams.get("node") ?? "";
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

  const { data: health, isLoading: healthLoading } = useHealth(nodeParam);
  const { data: statusEvents, isLoading: statusLoading } = useSystemEvents({
    from,
    to,
    node: nodeParam,
    scope: "status_changes",
    page: statusPage,
    page_size: 20,
  });
  const { data: technicalEvents, isLoading: technicalLoading } = useSystemEvents({
    from,
    to,
    node: nodeParam,
    scope: "technical_issues",
    page: technicalPage,
    page_size: 20,
  });
  const { data: activityEvents, isLoading: activityLoading } = useSystemEvents({
    from,
    to,
    node: nodeParam,
    scope: "all",
    event_group: activityType,
    page: activityPage,
    page_size: 20,
  });
  const { data: ingestRuns, isLoading: runsLoading } = useIngestRuns(nodeParam);

  const streams = health?.streams ?? [];
  const statusItems = statusEvents?.items ?? [];
  const technicalItems = technicalEvents?.items ?? [];
  const activityItems = activityEvents?.items ?? [];
  const runs = ingestRuns?.items ?? [];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-3">
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Kesehatan</h1>
        <NodeSelect
          value={node}
          onChange={(value) =>
            setQuery({ node: value || null, status_page: "1", technical_page: "1", activity_page: "1" })
          }
        />
      </div>

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

      <Card className="flex flex-wrap items-center gap-6">
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            Status Sensor
          </p>
          {healthLoading ? (
            <div className="h-6 w-20 animate-pulse rounded-full bg-[var(--color-border)]" />
          ) : (
            <Badge
              variant={health?.node_status ?? "no_data"}
              label={nodeStatusLabel(health?.node_status)}
            />
          )}
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
            Jeda Sinkronisasi
          </p>
          {healthLoading ? (
            <div className="h-6 w-16 animate-pulse rounded bg-[var(--color-border)]" />
          ) : (
            <span className="text-sm font-medium text-[var(--color-text)]">
              {fmtLag(health?.sync_lag_seconds ?? null)}
            </span>
          )}
        </div>
        {health?.node_id && (
          <div className="flex flex-col gap-1">
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
              ID Sensor
            </p>
            <span className="font-mono text-sm text-[var(--color-text)]">{health.node_id}</span>
          </div>
        )}
      </Card>

      <FreshnessTable streams={streams} loading={healthLoading} />

      <WanFailoverPanel health={health} healthLoading={healthLoading} />

      <BatchSuccessRate runs={runs} loading={runsLoading} />

      <SystemEventsList
        items={statusItems}
        loading={statusLoading}
        pagination={statusEvents?.meta ?? null}
        onPageChange={(page) => setQuery({ status_page: String(page) })}
        title="Riwayat Status Sensor"
        description="Menampilkan riwayat saat sensor atau Raspberry Pi terdeteksi offline lalu online kembali. Ini dipisah agar perubahan status lebih mudah dilihat."
        emptyMessage="Belum ada perubahan status sensor"
        emptyDetail="Saat ada sensor mati atau kembali aktif, riwayatnya akan muncul di sini."
        aggregateWarnings={false}
      />

      <SystemEventsList
        items={technicalItems}
        loading={technicalLoading}
        pagination={technicalEvents?.meta ?? null}
        onPageChange={(page) => setQuery({ technical_page: String(page) })}
        title="Log Gangguan Teknis"
        description="Menampilkan warning, error, dan gangguan teknis penting. Warning petir yang berulang diringkas agar tidak menutupi riwayat status sensor."
        emptyMessage="Tidak ada gangguan teknis terbaru"
        emptyDetail="Jika ada warning atau error penting dari ingest/server, riwayatnya akan muncul di sini."
        aggregateWarnings
      />

      <SystemEventsList
        items={activityItems}
        loading={activityLoading}
        pagination={activityEvents?.meta ?? null}
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
