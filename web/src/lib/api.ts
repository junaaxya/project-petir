import type {
  WeatherLatestResponse,
  HealthLatestResponse,
} from "./types";
import type {
  HistoryResponse,
  ApiError,
  LightningStatus,
  LightningEventType,
  QualityStatus,
  SystemLevel,
} from "@contracts";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

class ApiRequestError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    let code = "INTERNAL";
    let message = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as ApiError;
      code = body.error.code;
      message = body.error.message;
    } catch (_e) {
      void _e;
    }
    throw new ApiRequestError(code, message, res.status);
  }
  return res.json() as Promise<T>;
}

export function getWeatherLatest(node?: string): Promise<WeatherLatestResponse> {
  const q = node ? `?node=${encodeURIComponent(node)}` : "";
  return apiFetch<WeatherLatestResponse>(`/api/weather/latest${q}`);
}

export interface WeatherHistoryParams {
  from: string;
  to: string;
  interval: "raw" | "1m" | "5m" | "15m" | "1h";
  node?: string;
}

export function getWeatherHistory(params: WeatherHistoryParams): Promise<HistoryResponse> {
  const p = new URLSearchParams({
    from: params.from,
    to: params.to,
    interval: params.interval,
  });
  if (params.node) p.set("node", params.node);
  return apiFetch<HistoryResponse>(`/api/weather/history?${p.toString()}`);
}

export function getHealthLatest(node?: string): Promise<HealthLatestResponse> {
  const q = node ? `?node=${encodeURIComponent(node)}` : "";
  return apiFetch<HealthLatestResponse>(`/api/health/latest${q}`);
}

export interface LightningLatestMinute {
  minute_utc: string;
  source: string;
  device: string;
  status: LightningStatus | null;
  lightning_count: number | null;
  disturber_count: number | null;
  noise_window_count: number | null;
  noise_event_count: number | null;
  last_event_ts_utc: string | null;
  last_distance_km: number | null;
  max_energy_raw: number | null;
}

export interface LightningLatestResponse {
  node_id: string | null;
  minute: LightningLatestMinute | null;
}

export function getLightningLatest(node?: string): Promise<LightningLatestResponse> {
  const q = node ? `?node=${encodeURIComponent(node)}` : "";
  return apiFetch<LightningLatestResponse>(`/api/lightning/latest${q}`);
}

export interface LightningHistoryParams {
  from: string;
  to: string;
  interval: "1m" | "5m" | "15m" | "1h";
  node?: string;
}

export function getLightningHistory(params: LightningHistoryParams): Promise<HistoryResponse> {
  const p = new URLSearchParams({
    from: params.from,
    to: params.to,
    interval: params.interval,
  });
  if (params.node) p.set("node", params.node);
  return apiFetch<HistoryResponse>(`/api/lightning/history?${p.toString()}`);
}

export interface LightningEvent {
  edge_id: number;
  ts_pi_utc: string;
  event_type: LightningEventType | null;
  distance_km: number | null;
  energy_raw: number | null;
  noise_level: number | null;
  source: string | null;
  device: string | null;
}

export interface LightningEventsResponse {
  node_id: string | null;
  items: LightningEvent[];
  meta: { count: number };
}

export interface LightningEventsParams {
  from?: string;
  to?: string;
  event_type?: LightningEventType;
  node?: string;
  limit?: number;
}

export function getLightningEvents(params: LightningEventsParams): Promise<LightningEventsResponse> {
  const p = new URLSearchParams();
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.event_type) p.set("event_type", params.event_type);
  if (params.node) p.set("node", params.node);
  if (params.limit != null) p.set("limit", String(params.limit));
  const qs = p.toString();
  return apiFetch<LightningEventsResponse>(`/api/lightning/events${qs ? `?${qs}` : ""}`);
}

export interface SystemEvent {
  edge_id: number;
  ts_pi_utc: string;
  source: string | null;
  level: SystemLevel | null;
  event_type: string | null;
  message: string | null;
}

export interface SystemEventsResponse {
  node_id: string | null;
  items: SystemEvent[];
  meta: { count: number };
}

export interface SystemEventsParams {
  from?: string;
  to?: string;
  level?: SystemLevel;
  node?: string;
  limit?: number;
}

export function getSystemEvents(params: SystemEventsParams): Promise<SystemEventsResponse> {
  const p = new URLSearchParams();
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.level) p.set("level", params.level);
  if (params.node) p.set("node", params.node);
  if (params.limit != null) p.set("limit", String(params.limit));
  const qs = p.toString();
  return apiFetch<SystemEventsResponse>(`/api/system/events${qs ? `?${qs}` : ""}`);
}

export interface SystemSummaryResponse {
  node_id: string | null;
  from_utc: string;
  to_utc: string;
  total_events: number;
  counts_by_level: Record<string, number>;
  recent: SystemEvent[];
}

export interface SystemSummaryParams {
  from?: string;
  to?: string;
  node?: string;
}

export function getSystemSummary(params: SystemSummaryParams): Promise<SystemSummaryResponse> {
  const p = new URLSearchParams();
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.node) p.set("node", params.node);
  const qs = p.toString();
  return apiFetch<SystemSummaryResponse>(`/api/system/summary${qs ? `?${qs}` : ""}`);
}

export interface QualityEvent {
  edge_id: number;
  minute_utc: string | null;
  quality_status: QualityStatus | null;
  reason_codes: string | string[] | null;
  message: string | null;
  created_at_utc: string;
}

export interface QualityEventsResponse {
  node_id: string | null;
  items: QualityEvent[];
  meta: { count: number };
}

export interface QualityEventsParams {
  from?: string;
  to?: string;
  status?: QualityStatus;
  node?: string;
  limit?: number;
}

export function getQualityEvents(params: QualityEventsParams): Promise<QualityEventsResponse> {
  const p = new URLSearchParams();
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.status) p.set("status", params.status);
  if (params.node) p.set("node", params.node);
  if (params.limit != null) p.set("limit", String(params.limit));
  const qs = p.toString();
  return apiFetch<QualityEventsResponse>(`/api/weather/quality-events${qs ? `?${qs}` : ""}`);
}

export interface IngestRun {
  run_id: string;
  node_id: string | null;
  table: string | null;
  status: string;
  accepted: number;
  rejected: number;
  started_at_utc: string | null;
  duration_ms: number | null;
}

export interface IngestRunsResponse {
  items: IngestRun[];
  meta: { count: number };
}

export function getIngestRuns(node?: string): Promise<IngestRunsResponse> {
  const q = node ? `?node=${encodeURIComponent(node)}` : "";
  return apiFetch<IngestRunsResponse>(`/api/ingest/runs${q}`);
}

export { ApiRequestError };
