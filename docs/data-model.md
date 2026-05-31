# PetirDashboard — Data Model

Column-level reference for the six data tables as they exist on the edge SQLite and how they map to central PostgreSQL. Wire row shapes live in [`packages/contracts/schema/rows`](../packages/contracts/schema/rows).

## Edge to central mapping rules

Every central data table adds, beyond the edge columns:

- `node_id TEXT` — which edge node the row came from (FK `edge_nodes`).
- `db_epoch UUID` — edge DB generation, for reflash detection.
- `synced_at_utc TIMESTAMPTZ DEFAULT now()` — when the server stored it.
- `ingest_run_id UUID` (nullable, FK `sync_runs`) — which sync run delivered it.

Cursor columns:

- **append** tables carry the edge `id` as `edge_id`; central unique key `(node_id, db_epoch, edge_id)`.
- **summary** tables carry `change_seq`; central primary key `(node_id, minute_utc, source, device)`.

All edge timestamps are TEXT ISO-8601; central stores `timestamptz`.

## weather_samples (append)

| Edge column | Type | Central | Notes |
| --- | --- | --- | --- |
| id | INTEGER PK | edge_id BIGINT | cursor |
| ts_pi_utc | TEXT | timestamptz | sensor read time |
| source / device / sensor | TEXT | text | |
| temperature_c | REAL | double precision | |
| humidity_pct | REAL | double precision | |
| pressure_hpa | REAL | double precision | |
| illuminance_lux | REAL | double precision | log-scale in UI |
| rain_mm | REAL | double precision | |
| wind_speed_ms | REAL | double precision | |
| wind_dir_code | TEXT | text | |
| wind_dir_deg | REAL | double precision | |
| raw_json | TEXT | jsonb | full payload, ML-ready |
| ingest_run_id | TEXT | text | edge ingestion id, not sync run |
| created_at_utc | TEXT | timestamptz | |

## weather_minute_summary (summary)

Key `(node_id, minute_utc, source, device)`. Cursor `change_seq`.

| Group | Columns |
| --- | --- |
| identity | minute_utc, source, device |
| counts | sample_count, metric_sample_count, valid_sample_count, warn_sample_count, invalid_sample_count |
| status | status (ok/warn/degraded/invalid/no_data), degraded |
| temperature | temperature_avg/min/max |
| humidity | humidity_avg/min/max |
| pressure | pressure_avg/min/max |
| illuminance | illuminance_avg/min/max |
| rain | rain_max |
| wind | wind_speed_avg, wind_speed_max, latest_wind_dir_deg |
| timing | last_sample_ts_utc, updated_at_utc |

## lightning_events (append)

Sparse in the current deployment — UI must handle low/empty volume honestly.

| Edge column | Central | Notes |
| --- | --- | --- |
| id | edge_id | cursor |
| ts_pi_utc | timestamptz | |
| source / device / sensor | text | |
| event_type | text | lightning / disturber / noise |
| distance_km | double precision | nullable |
| energy_raw | bigint | |
| noise_level | int | |
| irq_source | text | |
| raw_line | text | |
| ingest_run_id | text | |
| created_at_utc | timestamptz | |

## lightning_minute_summary (summary)

Key `(node_id, minute_utc, source, device)`. Cursor `change_seq`.

| Group | Columns |
| --- | --- |
| identity | minute_utc, source, device |
| counts | lightning_count, disturber_count, noise_window_count, noise_event_count |
| status | status (quiet/noise/disturber/activity/no_data) |
| last event | last_event_ts_utc, last_distance_km, max_energy_raw |
| timing | updated_at_utc |

## weather_quality_events (append)

| Edge column | Central | Notes |
| --- | --- | --- |
| id | edge_id | cursor |
| ts_pi_utc / minute_utc / sample_ts_utc | timestamptz | all nullable |
| source / device | text | |
| quality_status | text | ok / warn / invalid |
| reason_codes | text/jsonb | JSON array or delimited |
| message | text | |
| details_json | jsonb | |
| created_at_utc | timestamptz | |

## system_events (append)

Synced first (highest priority).

| Edge column | Central | Notes |
| --- | --- | --- |
| id | edge_id | cursor |
| ts_pi_utc | timestamptz | |
| source | text | |
| level | text | debug/info/warn/error/critical |
| event_type | text | boot, error, sync_failure, clock_skew, ... |
| message | text | |
| details_json | jsonb | |
| created_at_utc | timestamptz | |

## Registry / sync tables (central only)

| Table | Key | Purpose |
| --- | --- | --- |
| edge_nodes | node_id | node registry, token hash, last_seen, enabled |
| sync_runs | run_id (UUID) | one row per edge sync run, counts, status, duration |
| sync_cursors | (node_id, table_name) | authoritative checkpoint: last_edge_id / last_change_seq, db_epoch |
