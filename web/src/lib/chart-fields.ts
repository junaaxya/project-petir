import type { HistoryPoint } from "@/lib/types";

type Row = HistoryPoint & Record<string, unknown>;

export function isRawSeries(series: Row[]): boolean {
  return series.length > 0 && "temperature_c" in series[0];
}

export function getRain(row: Row): number | null {
  return (row.rain_max as number | null) ?? (row.rain_mm as number | null) ?? null;
}

export function getWindSpeed(row: Row): number | null {
  return (row.wind_speed_avg as number | null) ?? (row.wind_speed_ms as number | null) ?? null;
}

export function getWindDir(row: Row): number | null {
  return (row.latest_wind_dir_deg as number | null) ?? (row.wind_dir_deg as number | null) ?? null;
}

export function getTempAvg(row: Row): number | null {
  return (row.temperature_avg as number | null) ?? (row.temperature_c as number | null) ?? null;
}

export function getTempMin(row: Row): number | null {
  return (row.temperature_min as number | null) ?? (row.temperature_c as number | null) ?? null;
}

export function getTempMax(row: Row): number | null {
  return (row.temperature_max as number | null) ?? (row.temperature_c as number | null) ?? null;
}

export function getHumidity(row: Row): number | null {
  return (row.humidity_avg as number | null) ?? (row.humidity_pct as number | null) ?? null;
}

export function getPressure(row: Row): number | null {
  return (row.pressure_avg as number | null) ?? (row.pressure_hpa as number | null) ?? null;
}

export function getIlluminance(row: Row): number | null {
  return (row.illuminance_avg as number | null) ?? (row.illuminance_lux as number | null) ?? null;
}