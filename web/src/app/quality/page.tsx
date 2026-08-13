"use client";

import { Suspense, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQualityEvents } from "@/hooks/useQualityEvents";
import { NodeSelect } from "@/components/common/NodeSelect";
import { HistoryFilterBar } from "@/components/common/HistoryFilterBar";
import { QualityEventsTable } from "@/components/quality/QualityEventsTable";
import { QualityDistribution } from "@/components/quality/QualityDistribution";
import { ReasonCodesBreakdown } from "@/components/quality/ReasonCodesBreakdown";
import {
  dateRangeToApiRange,
  normalizeDateRange,
  parseHistoryRangePreset,
  parsePositiveInt,
  presetToDateRange,
  type HistoryRangePreset,
} from "@/lib/historyFilters";
import type { QualityStatus } from "@contracts";

function QualityPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const node = searchParams.get("node") ?? "";
  const rangePreset = parseHistoryRangePreset(searchParams.get("range"));
  const page = parsePositiveInt(searchParams.get("page"), 1);
  const status = (searchParams.get("status") as QualityStatus | "all" | null) ?? "all";

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

  const { data, isLoading } = useQualityEvents({
    from,
    to,
    node: nodeParam,
    status: status === "all" ? undefined : status,
    page,
    page_size: 20,
  });

  const items = data?.items ?? [];
  const summary = data?.summary ?? null;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-3">
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Kualitas Data</h1>
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <QualityDistribution items={items} summary={summary} loading={isLoading} />
        <ReasonCodesBreakdown
          items={items}
          loading={isLoading}
          description="Breakdown ini mengikuti log kualitas yang sedang ditampilkan pada tabel di bawah, agar tetap ringan saat diaudit per halaman."
        />
      </div>

      <QualityEventsTable
        items={items}
        loading={isLoading}
        filter={status}
        onFilterChange={(value) => setQuery({ status: value === "all" ? null : value, page: "1" })}
        pagination={data?.meta ?? null}
        onPageChange={(nextPage) => setQuery({ page: String(nextPage) })}
      />
    </div>
  );
}

export default function QualityPage() {
  return (
    <Suspense fallback={<div className="h-24 animate-pulse rounded bg-[var(--color-border)]" />}>
      <QualityPageContent />
    </Suspense>
  );
}
