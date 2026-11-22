import type {
  DailyForecastResponse,
  LightningEventsExportResponse,
  LightningEventsResponse,
} from "./index";

const event = {
  edge_id: 42,
  ts_pi_utc: "2026-11-22T00:00:00+00:00",
  event_type: "lightning",
  distance_km: 12,
  energy_raw: 900,
  noise_level: 1,
  source: "arduino",
  device: "as3935",
} as const;

export const QUERY_CONTRACT_EXAMPLES = {
  dailyForecast: {
    node_id: "rpi-lab-01",
    forecast_date_wib: "2026-11-22",
    today_label: "22-11-2026",
    timezone: "Asia/Jakarta",
    computed_at_utc: "2026-11-22T00:00:00+00:00",
    status: "available",
    sample_count: 30,
    latest_sample_utc: "2026-11-22T00:00:00+00:00",
    items: [],
  } satisfies DailyForecastResponse,
  lightningEvents: {
    node_id: "rpi-lab-01",
    items: [event],
    meta: {
      count: 1,
      page: 1,
      page_size: 20,
      total_items: 1,
      total_pages: 1,
      has_prev: false,
      has_next: false,
      requested_limit: 200,
    },
  } satisfies LightningEventsResponse,
  lightningEventsExport: {
    node_id: "rpi-lab-01",
    items: [event],
    meta: { count: 1, scope: "all_filtered" },
  } satisfies LightningEventsExportResponse,
} as const;
