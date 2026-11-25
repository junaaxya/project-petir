export type {
  WeatherStatus,
  LightningStatus,
  NodeStatus,
  StreamKind,
  StreamStatus,
  WeatherMinuteSummaryRow,
  HistoryPoint,
  HistoryResponse,
  ApiError,
  WanFailoverPrimaryBadge,
  WanFailoverUplinkKind,
} from "@contracts";

import type {
  NodeStatus as ContractNodeStatus,
  StreamStatus as ContractStreamStatus,
  WanFailoverPrimaryBadge as ContractWanFailoverPrimaryBadge,
  WanFailoverUplinkKind as ContractWanFailoverUplinkKind,
} from "@contracts";

export interface WeatherLatestMinute {
  minute_utc: string;
  source: string;
  device: string;
  status: import("@contracts").WeatherStatus | null;
  degraded: boolean | null;
  sample_count: number | null;
  temperature_avg: number | null;
  temperature_min: number | null;
  temperature_max: number | null;
  humidity_avg: number | null;
  pressure_avg: number | null;
  illuminance_avg: number | null;
  rain_max: number | null;
  wind_speed_avg: number | null;
  wind_speed_max: number | null;
  latest_wind_dir_deg: number | null;
}

export interface WeatherLatestResponse {
  node_id: string | null;
  minute: WeatherLatestMinute | null;
}

export interface HealthStream {
  stream: string;
  updated_at_utc: string | null;
  age_seconds: number | null;
  status: ContractStreamStatus;
}

export interface WanFailoverHealthCheck {
  iface: string | null;
  connection: string | null;
  ipv4: string | null;
  gateway: string | null;
  ok: boolean | null;
  detail: string | null;
  route_metric: number | null;
}

export interface WanFailoverDecision {
  eth_fail_count: number | null;
  eth_recover_count: number | null;
  fail_threshold: number | null;
  recover_threshold: number | null;
  last_change: string | null;
  last_event: string | null;
}

export interface WanFailoverRoute {
  iface: string | null;
  gateway: string | null;
  metric: number | null;
  kind: string | null;
  raw: string | null;
}

export interface WanFailoverFrontendSummary {
  badge: ContractWanFailoverPrimaryBadge | null;
  message: string | null;
  recommended_color: string | null;
}

export interface WanFailoverEvent {
  ts_utc: string | null;
  event_type: string | null;
  active_uplink_iface: string | null;
  active_uplink_kind: ContractWanFailoverUplinkKind | string | null;
  message: string | null;
  details?: Record<string, unknown> | null;
}

export interface WanFailoverStatus {
  available: boolean;
  ts_utc: string | null;
  mode: string | null;
  active_uplink_iface: string | null;
  active_uplink_kind: ContractWanFailoverUplinkKind | string | null;
  primary_badge: ContractWanFailoverPrimaryBadge;
  message: string;
  decision: WanFailoverDecision;
  checks: {
    eth: WanFailoverHealthCheck;
    wifi: WanFailoverHealthCheck;
  };
  default_routes: WanFailoverRoute[];
  frontend_summary: WanFailoverFrontendSummary;
  recent_events: WanFailoverEvent[];
}

export interface HealthLatestResponse {
  station_status: ContractNodeStatus;
  data_availability: "available" | "degraded" | "unavailable";
  updated_at_utc: string | null;
  freshness: HealthStream[];
  disruption: {
    active: boolean;
    level: "none" | "warning" | "outage" | "unavailable";
  };
}

export interface HealthDiagnosticsResponse {
  node_id: string | null;
  wan_failover: WanFailoverStatus;
}
