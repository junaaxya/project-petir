# PetirDashboard — API Contract

Base path `/api`. All timestamps are UTC ISO-8601. The wire types are defined in [`packages/contracts`](../packages/contracts/README.md); this document is the human reference.

Two separated paths:

- **Write path** `/api/ingest/*` — node bearer token, write-only.
- **Read path** `/api/{weather,lightning,health,system}/*` — read-only, dashboard.

## Common conventions

- `from` / `to` — ISO-8601. Default `to = now`, `from = now - 24h`.
- `node` — node id. Defaults to the single active node.
- `interval` — one of `raw`, `1m`, `5m`, `15m`, `1h`.
- Pagination — `limit` (<= 1000) plus opaque `cursor`.
- Empty range returns `200` with `series: []` or `items: []`, never an error.

## Error shape

```json
{ "error": { "code": "BAD_RANGE", "message": "from must be < to" } }
```

| HTTP | code | When |
| --- | --- | --- |
| 400 | `BAD_RANGE` / `BAD_PARAM` | invalid params (`from >= to`, unknown interval) |
| 401 | `BAD_TOKEN` | missing/invalid node token (write path) |
| 403 | `NODE_DISABLED` | node registered but disabled |
| 404 | `NODE_NOT_FOUND` | unknown node |
| 409 | `NODE_MISMATCH` | `node_id` does not match token |
| 416 | `RANGE_TOO_LARGE` | raw range beyond limit (e.g. raw > 7 days) |
| 422 | `INVALID_ENVELOPE` | envelope fails contract validation |
| 426 | `CONTRACT_INCOMPATIBLE` | MAJOR contract version mismatch |
| 429 | `BACKPRESSURE` | server asking the node to slow down |
| 500 | `INTERNAL` | unexpected server error |

---

## Write path

### POST /api/ingest/sync-batch

Header: `Authorization: Bearer <node_token>`. One table per request, batch of rows. Body is the `SyncBatchEnvelope` (see contract).

Request:

```json
{
  "contract_version": "1.0.0",
  "node_id": "rpi-lab-01",
  "db_epoch": "11111111-2222-3333-4444-555555555555",
  "run_id": "9b1c2d3e-4f50-6172-8394-a5b6c7d8e9f0",
  "run": { "started_at_utc": "2026-05-30T03:16:00Z", "duration_ms": 142, "sequence": 2 },
  "table": "weather_minute_summary",
  "cursor": { "strategy": "summary", "last_change_seq": 5521 },
  "rows": [ { "change_seq": 5522, "minute_utc": "2026-05-30T03:15:00Z", "source": "arduino", "device": "weather-01", "status": "ok", "temperature_avg": 27.4, "updated_at_utc": "2026-05-30T03:16:01Z" } ]
}
```

Response `200`:

```json
{
  "run_id": "9b1c2d3e-4f50-6172-8394-a5b6c7d8e9f0",
  "table": "weather_minute_summary",
  "status": "accepted",
  "accepted": 1,
  "rejected": [],
  "accepted_cursor": { "strategy": "summary", "last_change_seq": 5522 },
  "server_contract_version": "1.0.0"
}
```

Semantics:

- Idempotent via natural-key upsert. Re-sending the same rows is safe.
- `accepted_cursor` is authoritative; the edge persists it verbatim.
- Per-row failures appear in `rejected[]` and the cursor still advances past them (quarantine).
- Whole-request failures use the error table above.

### GET /api/ingest/runs

Write-path telemetry, readable by the dashboard Health page.

Params: `node?`, `status?`, `limit`. Returns recent `sync_runs`.

---

## Read path

| Endpoint | Params | Returns |
| --- | --- | --- |
| `GET /api/health/latest` | `node?` | node status, per-stream freshness, sync lag |
| `GET /api/weather/latest` | `node?` | newest minute summary + last sample |
| `GET /api/weather/history` | `from,to,interval,node?,metrics?` | per-metric series (avg/min/max) |
| `GET /api/weather/quality-events` | `from,to,status?,node?,limit,cursor` | quality events (paginated) |
| `GET /api/lightning/latest` | `node?` | latest lightning status, last event, last distance |
| `GET /api/lightning/history` | `from,to,interval,node?` | count / disturber / noise per bucket |
| `GET /api/lightning/events` | `from,to,node?,limit,cursor` | raw events (paginated) |
| `GET /api/system/summary` | `from?,to?,node?` | counts per level/event_type + recent errors |

### History response shape

```json
{
  "node_id": "rpi-lab-01",
  "interval": "1h",
  "from": "2026-05-29T00:00:00Z",
  "to": "2026-05-30T00:00:00Z",
  "series": [
    { "bucket": "2026-05-29T00:00:00Z", "temperature_avg": 26.1, "temperature_min": 25.4,
      "temperature_max": 26.9, "humidity_avg": 84.0, "pressure_avg": 1009.1,
      "rain_max": 0.0, "wind_speed_avg": 1.1, "wind_speed_max": 2.4, "sample_count": 720 }
  ],
  "meta": { "count": 24, "downsampled": true }
}
```

### health/latest response shape

```json
{
  "node_id": "rpi-lab-01",
  "node_status": "ok",
  "last_seen_utc": "2026-05-30T03:16:05Z",
  "sync_lag_seconds": 4,
  "streams": [
    { "table": "weather_minute_summary", "last_ts_utc": "2026-05-30T03:16:01Z", "age_seconds": 4, "status": "fresh" },
    { "table": "lightning_minute_summary", "last_ts_utc": "2026-05-30T03:16:00Z", "age_seconds": 5, "status": "fresh" }
  ]
}
```

Freshness thresholds (defaults, tunable): `fresh` < 2x the send interval, `stale` < 5x, `offline` >= 5x or `last_seen` exceeded.
