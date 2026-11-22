"use client";

import { Suspense, useCallback, useEffect, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useWeatherHistory } from "@/hooks/useWeatherHistory";
import { NodeSelect } from "@/components/common/NodeSelect";
import { HistoryFilterBar } from "@/components/common/HistoryFilterBar";
import { IntervalSelector } from "@/components/weather/IntervalSelector";
import { TemperatureBandChart } from "@/components/weather/TemperatureBandChart";
import { RainChart } from "@/components/weather/RainChart";
import { WindRoseChart } from "@/components/weather/WindRoseChart";
import { WeatherMetricChart } from "@/components/weather/WeatherMetricChart";
import { WeatherDataTable } from "@/components/weather/WeatherDataTable";
import { DeferredChart } from "@/components/weather/DeferredChart";
import type { WeatherHistoryParams } from "@/lib/api";
import { getHumidity, getIlluminance, getPressure, getWindSpeed } from "@/lib/chart-fields";
import { formatChartBuckets, formatDataCoverage } from "@/lib/chartBuckets";
import {
  dateRangeToApiRange,
  normalizeDateRange,
  parseHistoryRangePreset,
  presetToDateRange,
  type HistoryRangePreset,
} from "@/lib/historyFilters";

type Interval = WeatherHistoryParams["interval"];

const RAW_LIMIT = 3000;

function WeatherPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const node = searchParams.get("node") ?? "";
  const rangePreset = parseHistoryRangePreset(searchParams.get("range"));
  const intervalParam = searchParams.get("interval");
  const interval: Interval =
    intervalParam === "raw" ||
    intervalParam === "1m" ||
    intervalParam === "5m" ||
    intervalParam === "15m" ||
    intervalParam === "1h"
      ? intervalParam
      : "1h";

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

  const setQuery = useCallback((updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value == null || value === "") next.delete(key);
      else next.set(key, value);
    }
    const qs = next.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [pathname, router, searchParams]);

  const handlePresetChange = (preset: HistoryRangePreset) => {
    if (preset === "custom") {
      setQuery({ range: "custom", from_date: fromDate, to_date: toDate });
      return;
    }
    setQuery({ range: preset, from_date: null, to_date: null });
  };

  const rangeDays = useMemo(() => {
    const start = new Date(`${fromDate}T00:00:00`).getTime();
    const end = new Date(`${toDate}T00:00:00`).getTime();
    return Math.max(1, Math.floor((end - start) / 86_400_000) + 1);
  }, [fromDate, toDate]);
  const rawDisabled = rangeDays > 7;

  useEffect(() => {
    if (rawDisabled && interval === "raw") {
      setQuery({ interval: "1h" });
    }
  }, [interval, rawDisabled, setQuery]);

  const requestParams = useMemo<WeatherHistoryParams>(
    () => ({
      from,
      to,
      interval,
      node: nodeParam,
      limit: interval === "raw" ? RAW_LIMIT : undefined,
    }),
    [from, to, interval, nodeParam],
  );

  const { data, isLoading } = useWeatherHistory(requestParams);
  const series = useMemo(() => data?.series ?? [], [data?.series]);
  const bucketLabels = useMemo(() => formatChartBuckets(series), [series]);
  const dataCoverage = useMemo(() => formatDataCoverage(series), [series]);
  const rawLimited = interval === "raw" && series.length >= RAW_LIMIT;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-3">
        <h1 className="text-lg font-semibold text-[var(--color-text)]">Detail Cuaca</h1>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <NodeSelect value={node} onChange={(value) => setQuery({ node: value || null })} />
          <IntervalSelector value={interval} onChange={(value) => setQuery({ interval: value })} disableRaw={rawDisabled} />
        </div>
      </div>

      <HistoryFilterBar
        preset={rangePreset}
        fromDate={fromDate}
        toDate={toDate}
        onPresetChange={handlePresetChange}
        onFromDateChange={(value) => setQuery({ range: "custom", from_date: value, to_date: toDate })}
        onToDateChange={(value) => setQuery({ range: "custom", from_date: fromDate, to_date: value })}
      />

      {(data?.meta || rawDisabled || rawLimited) && (
        <div className="flex flex-col gap-1 text-xs text-[var(--color-text-muted)]">
          {data?.meta && (
            <p>
              {data.meta.count} titik
              {data.meta.downsampled ? " · diringkas per interval" : ""}
              {data.node_id ? ` · lokasi sensor ${data.node_id}` : ""}
            </p>
          )}
          {rawDisabled && (
            <p>Data asli dinonaktifkan untuk rentang di atas 7 hari agar halaman tetap cepat dibuka.</p>
          )}
          {rawLimited && (
            <p>Data asli dibatasi ke 3000 data terbaru agar halaman tidak terlalu berat saat dibuka.</p>
          )}
        </div>
      )}

      <section className="flex flex-col gap-3">
        <div className="space-y-1">
          <h2 className="text-base font-semibold text-[var(--color-text)] sm:text-lg">Grafik Cuaca</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Setiap grafik ditampilkan terpisah agar lebih mudah dibaca dan lebih konsisten antar metrik.
          </p>
          {dataCoverage && (
            <p className="text-xs text-[var(--color-text-muted)]">
              Data tersedia pada rentang terpilih:{" "}
              <span className="font-medium text-[var(--color-text)]">{dataCoverage}</span>
              {` · ${series.length.toLocaleString("id-ID")} baris`}
            </p>
          )}
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <DeferredChart>
            <TemperatureBandChart series={series} buckets={bucketLabels} loading={isLoading} />
          </DeferredChart>
          <DeferredChart>
            <WeatherMetricChart
              title="Kelembapan"
              unitLabel="Kelembapan (%)"
              color="#38bdf8"
              areaColor="rgba(56,189,248,0.06)"
              series={series}
              buckets={bucketLabels}
              loading={isLoading}
              getValue={getHumidity}
              emptyMessage="Tidak ada data kelembapan"
              emptyDetail="Data kelembapan akan muncul setelah sensor kembali sinkron."
            />
          </DeferredChart>
          <DeferredChart>
            <WeatherMetricChart
              title="Tekanan Udara"
              unitLabel="Tekanan udara (hPa)"
              color="#a78bfa"
              areaColor="rgba(167,139,250,0.06)"
              series={series}
              buckets={bucketLabels}
              loading={isLoading}
              getValue={getPressure}
              emptyMessage="Tidak ada data tekanan udara"
              emptyDetail="Data tekanan udara akan muncul setelah sensor kembali sinkron."
            />
          </DeferredChart>
          <DeferredChart>
            <WeatherMetricChart
              title="Cahaya"
              unitLabel="Cahaya (lx)"
              color="#fbbf24"
              areaColor="rgba(251,191,36,0.06)"
              series={series}
              buckets={bucketLabels}
              loading={isLoading}
              getValue={getIlluminance}
              emptyMessage="Tidak ada data cahaya"
              emptyDetail="Data cahaya akan muncul setelah sensor kembali sinkron."
            />
          </DeferredChart>
          <DeferredChart>
            <RainChart series={series} buckets={bucketLabels} loading={isLoading} />
          </DeferredChart>
          <DeferredChart>
            <WeatherMetricChart
              title="Kecepatan Angin"
              unitLabel="Kecepatan angin (m/s)"
              color="#22c55e"
              areaColor="rgba(34,197,94,0.06)"
              series={series}
              buckets={bucketLabels}
              loading={isLoading}
              getValue={getWindSpeed}
              emptyMessage="Tidak ada data kecepatan angin"
              emptyDetail="Data kecepatan angin akan muncul setelah sensor kembali sinkron."
            />
          </DeferredChart>
          <DeferredChart minHeight={250}>
            <WindRoseChart series={series} loading={isLoading} />
          </DeferredChart>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <div className="space-y-1">
          <h2 className="text-base font-semibold text-[var(--color-text)] sm:text-lg">Data Sensor</h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Tabel ini menampilkan riwayat detail per titik data sesuai rentang waktu dan mode yang dipilih.
          </p>
        </div>
        <WeatherDataTable series={series} loading={isLoading} rawLimited={rawLimited} />
      </section>
    </div>
  );
}

export default function WeatherPage() {
  return (
    <Suspense fallback={<div className="h-24 animate-pulse rounded bg-[var(--color-border)]" />}>
      <WeatherPageContent />
    </Suspense>
  );
}
