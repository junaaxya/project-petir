// PetirDashboard shared wire contract (TypeScript).
// Mirrors ../schema/*.json. Consumed by the Next.js dashboard (web/) for both
// the ingest envelope shape and the read-path API response types.

export const CONTRACT_VERSION = "2.0.0";

export type TableName =
  | "weather_samples"
  | "weather_minute_summary"
  | "lightning_events"
  | "lightning_minute_summary"
  | "weather_quality_events"
  | "system_events";

export type CursorStrategy = "append" | "summary";
export type WeatherStatus = "ok" | "warn" | "degraded" | "invalid" | "no_data";
export type LightningStatus = "quiet" | "noise" | "disturber" | "activity" | "saturated" | "no_data";
export type LightningEventType = "lightning" | "disturber" | "noise";
export type QualityStatus = "ok" | "warn" | "invalid";
export type SystemLevel = "debug" | "info" | "warn" | "error" | "critical";
export type IngestStatus = "accepted" | "partial" | "rejected";

export interface Cursor {
  strategy?: CursorStrategy | null;
  last_edge_id?: number | null;
  last_change_seq?: number | null;
}

export interface RunMeta {
  started_at_utc?: string | null;
  duration_ms?: number | null;
  sequence?: number | null;
}

export interface SyncBatchEnvelope {
  contract_version: string;
  node_id: string;
  db_epoch: string;
  run_id: string;
  run?: RunMeta;
  table: TableName;
  cursor: Cursor;
  rows: Record<string, unknown>[];
}

export interface RejectedRow {
  index: number;
  reason: string;
  field?: string | null;
}

export interface SyncBatchResponse {
  run_id: string;
  table: TableName;
  status: IngestStatus;
  accepted: number;
  rejected: RejectedRow[];
  accepted_cursor: Cursor;
  server_contract_version: string;
}

export interface WeatherSampleRow {
  edge_id: number;
  ts_pi_utc: string;
  source?: string | null;
  device?: string | null;
  sensor?: string | null;
  temperature_c?: number | null;
  humidity_pct?: number | null;
  pressure_hpa?: number | null;
  illuminance_lux?: number | null;
  rain_mm?: number | null;
  wind_speed_ms?: number | null;
  wind_dir_code?: number | null;
  wind_dir_deg?: number | null;
  raw_json?: Record<string, unknown> | string | null;
  ingest_run_id?: number | null;
  created_at_utc: string;
}

export interface WeatherMinuteSummaryRow {
  change_seq: number;
  minute_utc: string;
  source: string;
  device: string;
  sample_count?: number | null;
  metric_sample_count?: number | null;
  valid_sample_count?: number | null;
  warn_sample_count?: number | null;
  invalid_sample_count?: number | null;
  status?: WeatherStatus | null;
  degraded?: boolean | null;
  temperature_avg?: number | null;
  temperature_min?: number | null;
  temperature_max?: number | null;
  humidity_avg?: number | null;
  humidity_min?: number | null;
  humidity_max?: number | null;
  pressure_avg?: number | null;
  pressure_min?: number | null;
  pressure_max?: number | null;
  illuminance_avg?: number | null;
  illuminance_min?: number | null;
  illuminance_max?: number | null;
  rain_max?: number | null;
  wind_speed_avg?: number | null;
  wind_speed_max?: number | null;
  latest_wind_dir_deg?: number | null;
  last_sample_ts_utc?: string | null;
  updated_at_utc: string;
}

export interface LightningEventRow {
  edge_id: number;
  ts_pi_utc: string;
  source?: string | null;
  device?: string | null;
  sensor?: string | null;
  event_type?: LightningEventType | null;
  distance_km?: number | null;
  energy_raw?: number | null;
  noise_level?: number | null;
  irq_source?: number | null;
  raw_line?: string | null;
  ingest_run_id?: number | null;
  created_at_utc: string;
}

export interface LightningMinuteSummaryRow {
  change_seq: number;
  minute_utc: string;
  source: string;
  device: string;
  lightning_count?: number | null;
  disturber_count?: number | null;
  noise_window_count?: number | null;
  noise_event_count?: number | null;
  status?: LightningStatus | null;
  last_event_ts_utc?: string | null;
  last_distance_km?: number | null;
  max_energy_raw?: number | null;
  updated_at_utc: string;
}

export interface WeatherQualityEventRow {
  edge_id: number;
  ts_pi_utc?: string | null;
  minute_utc?: string | null;
  sample_ts_utc?: string | null;
  source?: string | null;
  device?: string | null;
  quality_status?: QualityStatus | null;
  reason_codes?: string | string[] | null;
  message?: string | null;
  details_json?: Record<string, unknown> | string | null;
  created_at_utc: string;
}

export interface SystemEventRow {
  edge_id: number;
  ts_pi_utc: string;
  source?: string | null;
  level?: SystemLevel | null;
  event_type?: string | null;
  message?: string | null;
  details_json?: Record<string, unknown> | string | null;
  created_at_utc: string;
}

export interface HistoryPoint {
  bucket: string;
  [metric: string]: number | string | null;
}

export interface HistoryResponse {
  node_id: string;
  interval: string;
  from: string;
  to: string;
  series: HistoryPoint[];
  meta: { count: number; downsampled: boolean };
}

export interface ApiError {
  error: { code: string; message: string };
}
