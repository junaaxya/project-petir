import type {
  WeatherLatestResponse,
  HealthLatestResponse,
} from "./types";
import type {
  HistoryResponse,
  ApiError,
  DailyForecastResponse,
  LightningEventItem,
  LightningEventsExportResponse,
  LightningEventsResponse,
  LightningStatus,
  LightningEventType,
  PaginationMeta as ContractPaginationMeta,
  QualityStatus,
  SystemLevel,
} from "@contracts";

export type {
  DailyForecastItem,
  DailyForecastLevel,
  DailyForecastResponse,
  LightningEventsExportResponse,
  LightningEventsResponse,
} from "@contracts";
export type LightningEvent = LightningEventItem;
export type PaginationMeta = ContractPaginationMeta;

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

class ApiRequestError extends Error {
  public readonly payload?: Record<string, unknown>;

  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
    payload?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.payload = payload;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let code = "INTERNAL";
    let message = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as ApiError & Record<string, unknown>;
      code = body.error.code;
      message = body.error.message;
      throw new ApiRequestError(code, message, res.status, body);
    } catch (_e) {
      if (_e instanceof ApiRequestError) throw _e;
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

export function getDailyForecast(node?: string): Promise<DailyForecastResponse> {
  const q = node ? `?node=${encodeURIComponent(node)}` : "";
  return apiFetch<DailyForecastResponse>(`/api/weather/daily-forecast${q}`);
}

export interface WeatherHistoryParams {
  from: string;
  to: string;
  interval: "raw" | "1m" | "5m" | "15m" | "1h";
  node?: string;
  limit?: number;
}

export function getWeatherHistory(params: WeatherHistoryParams): Promise<HistoryResponse> {
  const p = new URLSearchParams({
    from: params.from,
    to: params.to,
    interval: params.interval,
  });
  if (params.node) p.set("node", params.node);
  if (params.limit != null) p.set("limit", String(params.limit));
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

export interface LightningEventsParams {
  from?: string;
  to?: string;
  event_type?: LightningEventType;
  node?: string;
  limit?: number;
  page?: number;
  page_size?: number;
}

export function getLightningEvents(params: LightningEventsParams): Promise<LightningEventsResponse> {
  const p = new URLSearchParams();
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.event_type) p.set("event_type", params.event_type);
  if (params.node) p.set("node", params.node);
  if (params.limit != null) p.set("limit", String(params.limit));
  if (params.page != null) p.set("page", String(params.page));
  if (params.page_size != null) p.set("page_size", String(params.page_size));
  const qs = p.toString();
  return apiFetch<LightningEventsResponse>(`/api/lightning/events${qs ? `?${qs}` : ""}`);
}

export function exportLightningEvents(params: LightningEventsParams): Promise<LightningEventsExportResponse> {
  const p = new URLSearchParams();
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.event_type) p.set("event_type", params.event_type);
  if (params.node) p.set("node", params.node);
  const qs = p.toString();
  return apiFetch<LightningEventsExportResponse>(`/api/lightning/events/export${qs ? `?${qs}` : ""}`);
}

export function getLatestLightningEvents(params: Pick<LightningEventsParams, "node" | "page_size"> = {}): Promise<LightningEventsResponse> {
  const p = new URLSearchParams();
  if (params.node) p.set("node", params.node);
  if (params.page_size != null) p.set("page_size", String(params.page_size));
  const qs = p.toString();
  return apiFetch<LightningEventsResponse>(`/api/lightning/events/latest${qs ? `?${qs}` : ""}`);
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
  meta: PaginationMeta;
}

export type SystemEventScope = "all" | "important" | "status_changes" | "technical_issues";
export type SystemEventGroup = "all" | "heartbeat" | "status" | "other";

export interface SystemEventsParams {
  from?: string;
  to?: string;
  level?: SystemLevel;
  node?: string;
  importantOnly?: boolean;
  scope?: SystemEventScope;
  event_group?: SystemEventGroup;
  limit?: number;
  page?: number;
  page_size?: number;
}

export function getSystemEvents(params: SystemEventsParams): Promise<SystemEventsResponse> {
  const p = new URLSearchParams();
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.level) p.set("level", params.level);
  if (params.node) p.set("node", params.node);
  if (params.importantOnly) p.set("important_only", "true");
  if (params.scope) p.set("scope", params.scope);
  if (params.event_group) p.set("event_group", params.event_group);
  if (params.limit != null) p.set("limit", String(params.limit));
  if (params.page != null) p.set("page", String(params.page));
  if (params.page_size != null) p.set("page_size", String(params.page_size));
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
  scope?: string;
}

export interface SystemSummaryParams {
  from?: string;
  to?: string;
  node?: string;
  importantOnly?: boolean;
  scope?: SystemEventScope;
}

export function getSystemSummary(params: SystemSummaryParams): Promise<SystemSummaryResponse> {
  const p = new URLSearchParams();
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.node) p.set("node", params.node);
  if (params.importantOnly) p.set("important_only", "true");
  if (params.scope) p.set("scope", params.scope);
  const qs = p.toString();
  return apiFetch<SystemSummaryResponse>(`/api/system/summary${qs ? `?${qs}` : ""}`);
}

export interface IngestRun {
  run_id: string;
  node_id: string | null;
  started_at_utc: string | null;
  received_at_utc: string | null;
  status: string;
  tables_count: number;
  accepted: number;
  rejected: number;
  duration_ms: number | null;
  error_detail: string | null;
}

export interface IngestRunsResponse {
  node_id: string | null;
  items: IngestRun[];
}

export async function getIngestRuns(node?: string): Promise<IngestRunsResponse> {
  const q = node ? `?node=${encodeURIComponent(node)}` : "";
  const rows = await apiFetch<Array<{
    run_id: string;
    node_id: string | null;
    started_at_utc: string | null;
    received_at_utc: string | null;
    status: string;
    tables_count: number;
    rows_accepted: number;
    rows_rejected: number;
    duration_ms: number | null;
    error_detail: string | null;
  }>>(`/api/ingest/runs${q}`);

  return {
    node_id: node ?? null,
    items: rows.map((row) => ({
      run_id: row.run_id,
      node_id: row.node_id,
      started_at_utc: row.started_at_utc,
      received_at_utc: row.received_at_utc,
      status: row.status,
      tables_count: row.tables_count,
      accepted: row.rows_accepted,
      rejected: row.rows_rejected,
      duration_ms: row.duration_ms,
      error_detail: row.error_detail,
    })),
  };
}

export interface QualityEvent {
  edge_id: number;
  minute_utc: string | null;
  quality_status: QualityStatus | null;
  reason_codes: string | string[] | null;
  message: string | null;
  created_at_utc: string;
}

export interface QualitySummaryCounts {
  ok: number;
  warn: number;
  invalid: number;
}

export interface QualitySummary {
  total_minutes: number;
  counts: QualitySummaryCounts;
  event_minutes?: {
    warn: number;
    invalid: number;
  };
  effective_counts?: QualitySummaryCounts;
}

export interface QualityEventsResponse {
  node_id: string | null;
  items: QualityEvent[];
  summary: QualitySummary;
  meta: PaginationMeta;
}

export interface QualityEventsParams {
  from?: string;
  to?: string;
  status?: QualityStatus;
  node?: string;
  limit?: number;
  page?: number;
  page_size?: number;
}

export function getQualityEvents(params: QualityEventsParams): Promise<QualityEventsResponse> {
  const p = new URLSearchParams();
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.status) p.set("status", params.status);
  if (params.node) p.set("node", params.node);
  if (params.limit != null) p.set("limit", String(params.limit));
  if (params.page != null) p.set("page", String(params.page));
  if (params.page_size != null) p.set("page_size", String(params.page_size));
  const qs = p.toString();
  return apiFetch<QualityEventsResponse>(`/api/weather/quality-events${qs ? `?${qs}` : ""}`);
}

export type SirenAuditStatus =
  | "queued"
  | "dispatched"
  | "acknowledged"
  | "executing"
  | "success"
  | "failed"
  | "rejected";

export type SirenAuditOperatorRole = "admin" | "operator";

export interface SirenAuditNodeOption {
  nodeId: string;
  name: string | null;
  location: string | null;
  availabilityStatus: string | null;
  lastSeenUtc: string | null;
  eligible: boolean;
}

export interface SirenAuditOperatorOption {
  id: string;
  name: string | null;
  role: SirenAuditOperatorRole;
}

export interface SirenAuditOptionsResponse {
  nodes: SirenAuditNodeOption[];
  operators: SirenAuditOperatorOption[];
  limits: {
    durationSec: { min: number; max: number };
    repeats: { min: number; max: number };
    gapSec: { min: number; max: number };
    cooldownSeconds: number;
  };
  auth: {
    dashboardAuthEnabled: boolean;
    operatorAllowlistConfigured: boolean;
    allowedRoles: string[];
  };
}

export interface SirenAuditCommandPayload {
  type: "siren_audit_test";
  requestId: string;
  nodeId: string;
  parameters: {
    durationSec: number;
    repeats: number;
    gapSec: number;
  };
  requestedBy: string;
  requestedRole: SirenAuditOperatorRole;
  requestedAt: string;
  reason: string;
}

export interface SirenAuditHistoryItem {
  id: number;
  requestId: string;
  nodeId: string;
  requestedBy: string;
  requestedRole: SirenAuditOperatorRole;
  requestedAt: string;
  durationSec: number;
  repeats: number;
  gapSec: number;
  reason: string;
  status: SirenAuditStatus;
  resultMessage: string | null;
  cooldownUntil: string;
  cooldownRemainingSeconds: number;
  executedAt: string | null;
  updatedAt: string;
  command?: SirenAuditCommandPayload | null;
  resultDetails?: Record<string, unknown> | null;
}

export interface SirenAuditStatusUpdateItem {
  status: SirenAuditStatus;
  message: string | null;
  details: Record<string, unknown> | null;
  reportedBy: string | null;
  reportedAt: string;
}

export interface SirenAuditLatestResponse {
  nodeId: string | null;
  latest: SirenAuditHistoryItem | null;
  statusUpdates: SirenAuditStatusUpdateItem[];
}

export interface SirenAuditHistoryParams {
  from?: string;
  to?: string;
  node?: string;
  status?: SirenAuditStatus;
  page?: number;
  page_size?: number;
}

export interface SirenAuditHistoryResponse {
  nodeId: string | null;
  status: string | null;
  fromUtc: string;
  toUtc: string;
  items: SirenAuditHistoryItem[];
  meta: PaginationMeta;
}

export interface CreateSirenAuditPayload {
  nodeId: string;
  requestedBy: string;
  durationSec: number;
  repeats: number;
  gapSec: number;
  reason: string;
}

export interface CreateSirenAuditResponse extends SirenAuditHistoryItem {
  command: SirenAuditCommandPayload;
}

export function getSirenAuditOptions(): Promise<SirenAuditOptionsResponse> {
  return apiFetch<SirenAuditOptionsResponse>("/api/siren/audit-test/options");
}

export function getSirenAuditLatest(node?: string): Promise<SirenAuditLatestResponse> {
  const q = node ? `?node=${encodeURIComponent(node)}` : "";
  return apiFetch<SirenAuditLatestResponse>(`/api/siren/audit-test/latest${q}`);
}

export function getSirenAuditHistory(params: SirenAuditHistoryParams): Promise<SirenAuditHistoryResponse> {
  const p = new URLSearchParams();
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.node) p.set("node", params.node);
  if (params.status) p.set("status", params.status);
  if (params.page != null) p.set("page", String(params.page));
  if (params.page_size != null) p.set("page_size", String(params.page_size));
  const qs = p.toString();
  return apiFetch<SirenAuditHistoryResponse>(`/api/siren/audit-test/history${qs ? `?${qs}` : ""}`);
}

export function createSirenAuditRequest(payload: CreateSirenAuditPayload): Promise<CreateSirenAuditResponse> {
  return apiFetch<CreateSirenAuditResponse>("/api/siren/audit-test", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export { ApiRequestError };
