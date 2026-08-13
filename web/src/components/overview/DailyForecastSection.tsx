"use client";

import { useMemo } from "react";
import { Card } from "@/components/common/Card";
import { useWeatherHistory } from "@/hooks/useWeatherHistory";
import { getHumidity, getIlluminance, getPressure, getRain, getTempAvg } from "@/lib/chart-fields";
import type { HistoryPoint } from "@/lib/types";

type ForecastLevel = "rendah" | "sedang" | "tinggi";
type ForecastKind = "petir" | "hujan" | "angin";
type HistoryRow = HistoryPoint & Record<string, unknown>;

interface ForecastSnapshot {
  kind: ForecastKind;
  label: string;
  score: number;
  level: ForecastLevel;
  peakWindow: string | null;
  reasons: string[];
}

interface ScoredPoint {
  bucket: string;
  petir: number;
  hujan: number;
  angin: number;
  petirReasons: string[];
  hujanReasons: string[];
  anginReasons: string[];
}

interface BaselineStats {
  humidityHigh: number;
  humidityRise60: number;
  pressureDrop180: number;
  pressureDrop60: number;
  tempDrop60: number;
  brightLux: number;
  luxDropPct30: number;
  windRise30: number;
  windHigh: number;
  tempHot: number;
}

interface FutureHourScore {
  hour: number;
  petir: number;
  hujan: number;
  angin: number;
}

const LOW_LEVEL: ForecastLevel = "rendah";
const WIB_TIMEZONE = "Asia/Jakarta";

function getForecastRangesWib(now = new Date()) {
  const wibDate = new Date(now.toLocaleString("en-US", { timeZone: WIB_TIMEZONE }));
  const yyyy = wibDate.getFullYear();
  const mm = String(wibDate.getMonth() + 1).padStart(2, "0");
  const dd = String(wibDate.getDate()).padStart(2, "0");
  const todayStart = `${yyyy}-${mm}-${dd}T00:00:00+07:00`;
  const todayEnd = `${yyyy}-${mm}-${dd}T23:59:59.999+07:00`;

  const baselineStartDate = new Date(wibDate);
  baselineStartDate.setDate(baselineStartDate.getDate() - 7);
  const baselineEndDate = new Date(wibDate);
  baselineEndDate.setDate(baselineEndDate.getDate() - 1);

  const startY = baselineStartDate.getFullYear();
  const startM = String(baselineStartDate.getMonth() + 1).padStart(2, "0");
  const startD = String(baselineStartDate.getDate()).padStart(2, "0");
  const endY = baselineEndDate.getFullYear();
  const endM = String(baselineEndDate.getMonth() + 1).padStart(2, "0");
  const endD = String(baselineEndDate.getDate()).padStart(2, "0");

  return {
    todayFrom: todayStart,
    todayTo: todayEnd,
    todayLabel: `${dd}-${mm}-${yyyy}`,
    baselineFrom: `${startY}-${startM}-${startD}T00:00:00+07:00`,
    baselineTo: `${endY}-${endM}-${endD}T23:59:59.999+07:00`,
  };
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function getWindMax(row: HistoryRow): number | null {
  return asNumber(row.wind_speed_max) ?? asNumber(row.wind_speed_avg) ?? asNumber(row.wind_speed_ms);
}

function parseLocalHour(bucket: string): number {
  return Number(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: WIB_TIMEZONE,
      hour: "2-digit",
      hour12: false,
    }).format(new Date(bucket)),
  );
}

function getWibNowParts(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: WIB_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(now);

  const hour = Number(parts.find((part) => part.type === "hour")?.value ?? "0");
  const minute = Number(parts.find((part) => part.type === "minute")?.value ?? "0");
  return { hour, minute };
}

function formatHourWindow(startHour: number): string {
  const endHour = Math.min(startHour + 1, 23);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${pad(startHour)}.00–${pad(endHour)}.59`;
}

function levelFromScore(kind: ForecastKind, score: number): ForecastLevel {
  if (kind === "petir") return score >= 5 ? "tinggi" : score >= 2.5 ? "sedang" : "rendah";
  if (kind === "hujan") return score >= 4.5 ? "tinggi" : score >= 2.5 ? "sedang" : "rendah";
  return score >= 3.5 ? "tinggi" : score >= 2 ? "sedang" : "rendah";
}

function percentile(values: number[], q: number, fallback: number): number {
  const clean = values.filter((value) => Number.isFinite(value)).sort((a, b) => a - b);
  if (clean.length === 0) return fallback;
  const index = Math.min(clean.length - 1, Math.max(0, Math.floor(q * (clean.length - 1))));
  return clean[index] ?? fallback;
}

function positiveDiffs(values: Array<number | null>, lag: number, transform: (current: number, previous: number) => number) {
  const diffs: number[] = [];
  for (let index = lag; index < values.length; index += 1) {
    const current = values[index];
    const previous = values[index - lag];
    if (current == null || previous == null) continue;
    const diff = transform(current, previous);
    if (Number.isFinite(diff) && diff > 0) diffs.push(diff);
  }
  return diffs;
}

function average(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function getKindScore(point: ScoredPoint, kind: ForecastKind): number {
  return kind === "petir" ? point.petir : kind === "hujan" ? point.hujan : point.angin;
}

function getKindReasons(point: ScoredPoint, kind: ForecastKind): string[] {
  return kind === "petir" ? point.petirReasons : kind === "hujan" ? point.hujanReasons : point.anginReasons;
}

function buildBaseline(series: HistoryRow[]): BaselineStats {
  const humidity = series.map((row) => getHumidity(row));
  const pressure = series.map((row) => getPressure(row));
  const temperature = series.map((row) => getTempAvg(row));
  const illuminance = series.map((row) => getIlluminance(row));
  const wind = series.map((row) => getWindMax(row));

  return {
    humidityHigh: Math.max(80, percentile(humidity.filter((value): value is number => value != null), 0.9, 85)),
    humidityRise60: Math.max(3.5, percentile(positiveDiffs(humidity, 60, (current, previous) => current - previous), 0.9, 5.5)),
    pressureDrop180: Math.max(1.2, percentile(positiveDiffs(pressure, 180, (current, previous) => previous - current), 0.9, 2)),
    pressureDrop60: Math.max(0.5, percentile(positiveDiffs(pressure, 60, (current, previous) => previous - current), 0.9, 1)),
    tempDrop60: Math.max(0.8, percentile(positiveDiffs(temperature, 60, (current, previous) => previous - current), 0.9, 1.5)),
    brightLux: Math.max(20_000, percentile(illuminance.filter((value): value is number => value != null), 0.75, 20_000)),
    luxDropPct30: Math.max(55, percentile(positiveDiffs(illuminance, 30, (current, previous) => ((previous - current) / Math.max(previous, 1)) * 100), 0.9, 75)),
    windRise30: Math.max(0.06, percentile(positiveDiffs(wind, 30, (current, previous) => current - previous), 0.9, 0.09)),
    windHigh: Math.max(0.2, percentile(wind.filter((value): value is number => value != null), 0.9, 0.31)),
    tempHot: Math.max(31, percentile(temperature.filter((value): value is number => value != null), 0.9, 35)),
  };
}

function scoreSeries(series: HistoryRow[], baseline: BaselineStats): ScoredPoint[] {
  return series.map((row, index) => {
    const prev30 = index >= 30 ? series[index - 30] : null;
    const prev60 = index >= 60 ? series[index - 60] : null;
    const prev180 = index >= 180 ? series[index - 180] : null;

    const humidity = getHumidity(row);
    const pressure = getPressure(row);
    const temperature = getTempAvg(row);
    const illuminance = getIlluminance(row);
    const windMax = getWindMax(row) ?? 0;
    const rain = getRain(row) ?? 0;

    const hum60Up = humidity != null && prev60 ? humidity - (getHumidity(prev60) ?? humidity) : null;
    const press180Drop = pressure != null && prev180 ? (getPressure(prev180) ?? pressure) - pressure : null;
    const press60Drop = pressure != null && prev60 ? (getPressure(prev60) ?? pressure) - pressure : null;
    const temp60Drop = temperature != null && prev60 ? (getTempAvg(prev60) ?? temperature) - temperature : null;
    const prevLux30 = prev30 ? getIlluminance(prev30) : null;
    const lux30DropPct = illuminance != null && prevLux30 != null && prevLux30 > 0
      ? ((prevLux30 - illuminance) / prevLux30) * 100
      : null;
    const wind30Up = prev30 ? windMax - (getWindMax(prev30) ?? windMax) : null;
    const localHour = parseLocalHour(String(row.bucket));

    let petir = 0;
    let hujan = 0;
    let angin = 0;
    const petirReasons: string[] = [];
    const hujanReasons: string[] = [];
    const anginReasons: string[] = [];

    if (humidity != null && humidity >= baseline.humidityHigh) {
      petir += 2;
      hujan += 2;
      petirReasons.push("kelembapan masih tinggi");
      hujanReasons.push("kelembapan masih tinggi");
    }
    if (hum60Up != null && hum60Up >= baseline.humidityRise60) {
      petir += 1;
      hujan += 1;
      petirReasons.push("kelembapan naik cepat");
      hujanReasons.push("kelembapan naik cepat");
    }
    if (press180Drop != null && press180Drop >= baseline.pressureDrop180) {
      petir += 2;
      hujan += 1;
      petirReasons.push("tekanan terus menurun");
      hujanReasons.push("tekanan terus menurun");
    }
    if (temp60Drop != null && temp60Drop >= baseline.tempDrop60) {
      petir += 1;
      hujan += 1;
      petirReasons.push("suhu mulai turun");
      hujanReasons.push("suhu mulai turun");
    }
    if (prevLux30 != null && prevLux30 >= baseline.brightLux && lux30DropPct != null && lux30DropPct >= baseline.luxDropPct30) {
      petir += 1;
      hujan += 2;
      petirReasons.push("cahaya turun mendadak");
      hujanReasons.push("cahaya turun mendadak");
    }
    if (wind30Up != null && wind30Up >= baseline.windRise30) {
      petir += 1;
      angin += 2;
      petirReasons.push("angin mulai meningkat");
      anginReasons.push("angin mulai meningkat");
    }
    if (localHour >= 12 && localHour <= 18) {
      petir += 1;
      petirReasons.push("masuk jam rawan siang-sore");
    }

    if (windMax >= baseline.windHigh) {
      angin += 2;
      anginReasons.push("kecepatan angin cukup tinggi");
    }
    if (press60Drop != null && press60Drop >= baseline.pressureDrop60) {
      angin += 1;
      anginReasons.push("tekanan turun dalam 1 jam terakhir");
    }
    if (temperature != null && temperature >= baseline.tempHot) {
      angin += 1;
      anginReasons.push("udara siang cukup panas");
    }
    if (rain > 0) {
      hujan += 2;
      hujanReasons.push("sensor hujan sudah mulai aktif");
    }

    return {
      bucket: String(row.bucket),
      petir,
      hujan,
      angin,
      petirReasons,
      hujanReasons,
      anginReasons,
    };
  });
}

function buildFutureHourScores(baselineScored: ScoredPoint[], todayScored: ScoredPoint[]): FutureHourScore[] {
  const { hour: nowHour, minute: nowMinute } = getWibNowParts();
  const startHour = nowMinute > 0 ? Math.min(nowHour + 1, 23) : nowHour;
  const hourlyMap = new Map<number, { petir: number[]; hujan: number[]; angin: number[] }>();

  for (const point of baselineScored) {
    const hour = parseLocalHour(point.bucket);
    const slot = hourlyMap.get(hour) ?? { petir: [], hujan: [], angin: [] };
    slot.petir.push(point.petir);
    slot.hujan.push(point.hujan);
    slot.angin.push(point.angin);
    hourlyMap.set(hour, slot);
  }

  const recentWindowStart = Date.now() - 1000 * 60 * 90;
  const recentPoints = todayScored.filter((point) => {
    const ts = new Date(point.bucket).getTime();
    return Number.isFinite(ts) && ts >= recentWindowStart;
  });

  const momentum = {
    petir: Math.max(0, ...recentPoints.map((point) => point.petir), 0),
    hujan: Math.max(0, ...recentPoints.map((point) => point.hujan), 0),
    angin: Math.max(0, ...recentPoints.map((point) => point.angin), 0),
  };

  const results: FutureHourScore[] = [];
  for (let hour = startHour; hour <= 23; hour += 1) {
    const slot = hourlyMap.get(hour);
    const distance = hour - startHour;
    const decay = distance === 0 ? 1 : distance === 1 ? 0.72 : distance === 2 ? 0.45 : distance === 3 ? 0.25 : 0.1;

    results.push({
      hour,
      petir: average(slot?.petir ?? []) + momentum.petir * decay,
      hujan: average(slot?.hujan ?? []) + momentum.hujan * decay,
      angin: average(slot?.angin ?? []) + momentum.angin * decay,
    });
  }

  return results;
}

function summarize(kind: ForecastKind, todayScored: ScoredPoint[], futureHours: FutureHourScore[]): ForecastSnapshot {
  const label = kind === "petir" ? "Potensi Petir" : kind === "hujan" ? "Potensi Hujan" : "Potensi Angin Kencang";
  if (futureHours.length === 0) {
    return { kind, label, score: 0, level: LOW_LEVEL, peakWindow: null, reasons: ["Sisa hari ini sudah tidak panjang"] };
  }

  const recentWindowStart = Date.now() - 1000 * 60 * 120;
  const recentTop = [...todayScored]
    .filter((point) => {
      const ts = new Date(point.bucket).getTime();
      return Number.isFinite(ts) && ts >= recentWindowStart;
    })
    .sort((a, b) => {
      const scoreDiff = getKindScore(b, kind) - getKindScore(a, kind);
      if (scoreDiff !== 0) return scoreDiff;
      return new Date(b.bucket).getTime() - new Date(a.bucket).getTime();
    })[0];

  const topHour = [...futureHours].sort((a, b) => {
    const scoreA = kind === "petir" ? a.petir : kind === "hujan" ? a.hujan : a.angin;
    const scoreB = kind === "petir" ? b.petir : kind === "hujan" ? b.hujan : b.angin;
    if (scoreB !== scoreA) return scoreB - scoreA;
    return a.hour - b.hour;
  })[0];

  const score = kind === "petir" ? topHour.petir : kind === "hujan" ? topHour.hujan : topHour.angin;
  const level = levelFromScore(kind, score);
  const reasons = recentTop ? getKindReasons(recentTop, kind).slice(0, 2) : [];

  if (reasons.length === 0) {
    if (level === "rendah") {
      if (kind === "petir") reasons.push("belum terlihat sinyal petir yang kuat untuk sisa hari ini");
      else if (kind === "hujan") reasons.push("belum terlihat sinyal hujan yang kuat untuk sisa hari ini");
      else reasons.push("belum terlihat sinyal angin kencang yang kuat untuk sisa hari ini");
    } else {
      if (kind === "petir") reasons.push("potensi meningkat di jam berikutnya");
      else if (kind === "hujan") reasons.push("potensi hujan masih terbuka di jam berikutnya");
      else reasons.push("angin berpotensi menguat di jam berikutnya");
    }
  }

  return {
    kind,
    label,
    score,
    level,
    peakWindow: level === "rendah" ? null : formatHourWindow(topHour.hour),
    reasons,
  };
}

function levelStyles(level: ForecastLevel) {
  if (level === "tinggi") {
    return { badge: "border-red-500/30 bg-red-500/10 text-red-300", dot: "bg-red-400" };
  }
  if (level === "sedang") {
    return { badge: "border-amber-500/30 bg-amber-500/10 text-amber-300", dot: "bg-amber-400" };
  }
  return { badge: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300", dot: "bg-emerald-400" };
}

function levelLabel(level: ForecastLevel) {
  return level === "tinggi" ? "Tinggi" : level === "sedang" ? "Sedang" : "Rendah";
}

function ForecastCard({ item }: { item: ForecastSnapshot }) {
  const styles = levelStyles(item.level);
  const baseTimeLabel = item.kind === "petir"
    ? "Perkiraan waktu petir"
    : item.kind === "hujan"
      ? "Perkiraan waktu hujan"
      : "Perkiraan waktu angin kencang";

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">{item.label}</p>
          <div className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${styles.badge}`}>
            <span className={`inline-flex h-2 w-2 rounded-full ${styles.dot}`} aria-hidden="true" />
            {levelLabel(item.level)}
          </div>
        </div>
        <div className="text-right">
          <p className="text-[11px] text-[var(--color-text-muted)]">{baseTimeLabel}</p>
          <p className="text-sm font-semibold text-[var(--color-text)]">{item.peakWindow ? `${item.peakWindow} WIB` : "Belum ada waktu dominan"}</p>
        </div>
      </div>
      <p className="text-sm text-[var(--color-text-muted)]">{item.reasons.join(" • ")}</p>
    </Card>
  );
}

export function DailyForecastSection({ node }: { node?: string }) {
  const ranges = useMemo(() => getForecastRangesWib(), []);

  const todayQuery = useWeatherHistory({
    from: ranges.todayFrom,
    to: ranges.todayTo,
    interval: "1m",
    node,
    limit: 1600,
  });

  const baselineQuery = useWeatherHistory({
    from: ranges.baselineFrom,
    to: ranges.baselineTo,
    interval: "1m",
    node,
    limit: 10000,
  });

  const forecasts = useMemo(() => {
    const todaySeries = ((todayQuery.data?.series as HistoryRow[] | undefined) ?? []).filter((row) => row.bucket);
    const baselineSeries = ((baselineQuery.data?.series as HistoryRow[] | undefined) ?? []).filter((row) => row.bucket);
    const baseline = buildBaseline(baselineSeries.length > 0 ? baselineSeries : todaySeries);
    const todayScored = scoreSeries(todaySeries, baseline);
    const baselineScored = scoreSeries(baselineSeries.length > 0 ? baselineSeries : todaySeries, baseline);
    const futureHours = buildFutureHourScores(baselineScored, todayScored);
    return [
      summarize("petir", todayScored, futureHours),
      summarize("hujan", todayScored, futureHours),
      summarize("angin", todayScored, futureHours),
    ];
  }, [baselineQuery.data?.series, todayQuery.data?.series]);

  const isLoading = todayQuery.isLoading || baselineQuery.isLoading;

  return (
    <section className="flex flex-col gap-3">
      <div className="space-y-1">
        <h2 className="text-base font-semibold text-[var(--color-text)] sm:text-lg">Prediksi Hari Ini</h2>
        <p className="text-sm text-[var(--color-text-muted)]">
          Hari ini {ranges.todayLabel} (WIB)
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, idx) => (
            <div key={idx} className="h-36 animate-pulse rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {forecasts.map((item) => (
            <ForecastCard key={item.kind} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}
