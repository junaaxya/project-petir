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
} from "@contracts";

import type {
  NodeStatus as ContractNodeStatus,
  StreamKind as ContractStreamKind,
  StreamStatus as ContractStreamStatus,
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
  table: string;
  kind: ContractStreamKind;
  last_ts_utc: string | null;
  age_seconds: number | null;
  status: ContractStreamStatus;
}

export interface HealthLatestResponse {
  node_id: string | null;
  node_status: ContractNodeStatus;
  last_seen_utc: string | null;
  sync_lag_seconds: number | null;
  streams: HealthStream[];
}
