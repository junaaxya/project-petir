# PetirDashboard — Architecture

Weather + lightning monitoring. Sensors are read by an Arduino, buffered on a Raspberry Pi edge node (SQLite), pushed to a lab server (PostgreSQL), and visualized in a Next.js dashboard.

This document is the canonical architecture reference. For the wire protocol see [sync.md](./sync.md), for endpoints see [api-contract.md](./api-contract.md), for the table-by-table column map see [data-model.md](./data-model.md).

## Hard constraints

1. Raspberry Pi is an **edge collector only** — ingestion, local buffer, local health, light export. No dashboard workload.
2. The dashboard does **not** run on the Pi.
3. The lab server runs the central database, the backend API, and the frontend.
4. Data moves by **PUSH** from Pi to server. The server never live-queries the Pi SQLite.
5. Central DB is **PostgreSQL**.
6. Sync is **incremental**, never a repeated full dump.
7. The system tolerates a temporary Pi to server outage.
8. Sync is **retryable and resumable**.
9. Sync cursors are **clock-independent** (monotonic id / change_seq, not timestamps).

## Zones

```
+--------------- EDGE: Raspberry Pi (lightweight) ---------------+
| Arduino (weather + lightning)                                  |
|        | serial                                                |
|        v                                                       |
|  Ingestion service ---> SQLite (buffer + source of field data) |
|        |                      ^                                 |
|        |                      | incremental read (id/change_seq)|
|        v                      |                                 |
|  Local health.json      Sync Worker (single-run, systemd timer) |
|                               |  - read local cursor            |
|                               |  - select rows > cursor          |
|                               |  - POST batch (HTTPS + token)    |
|                               |  - advance cursor ONLY on ACK    |
+-------------------------------|--------------------------------+
                                | HTTPS push (incremental, idempotent)
                                v
+--------------- SERVER LAB ------------------------------------+
|  FastAPI                                                      |
|   |- POST /api/ingest/sync-batch   (WRITE path / upsert)      |
|   \- GET  /api/...                  (READ path / dashboard)   |
|        |                                                      |
|        v                                                      |
|  PostgreSQL (central, source of truth for history)           |
|   - mirror tables + node_id + db_epoch                        |
|   - edge_nodes, sync_runs, sync_cursors                       |
|        ^                                                      |
|        | query                                                |
|  Next.js dashboard (Overview / Weather / Lightning /          |
|                     Health / Quality)                         |
+--------------------------------------------------------------+
```

## Responsibilities

### Edge node (Raspberry Pi)

- Read sensors via Arduino, write to local SQLite.
- Compute local health snapshot.
- Run the sync worker as a **single-run job** on a systemd timer (not a long-lived daemon). Each run: read cursor, select new rows, push, advance cursor on ACK, exit. Exit code is the health signal.
- May prune already-ACKed raw rows after a grace period. Never prunes before ACK.
- Does **not** serve dashboard queries.

### Sync service (on the Pi)

The only egress path for field data. Stateless except for the local cursor table. Idempotent, resumable, retry with bounded backoff per run. Detailed in [sync.md](./sync.md).

### Server lab

Receives batches, validates against the shared contract, upserts to PostgreSQL, updates cursors and the node registry. PostgreSQL is the source of truth for history. Also hosts the API and the frontend.

### Backend (FastAPI)

Two clearly separated paths:

- **Write path** (`app/ingest/`) — `POST /api/ingest/sync-batch`. Auth: per-node bearer token. Only registered, enabled nodes may write. Strict per-node rate limiting / backpressure (`429`).
- **Read path** (`app/query/`) — dashboard GETs. Read-only. Optional dashboard-user auth in Phase 4; open-read on the internal lab network before that.

Node credentials can never read; dashboard users can never write. The two paths share neither auth nor service code.

### Frontend (Next.js)

Consumes the read API only. Five pages: Overview, Weather History, Lightning, Health, Data Quality. Components are organized per domain. The frontend has no knowledge of the Pi SQLite.

## Data classes (kept separate everywhere)

| Class | Source tables | Nature | Used for |
| --- | --- | --- | --- |
| Realtime snapshot | latest summary rows, health | volatile | Overview badges |
| Historical aggregate | `weather_minute_summary`, `lightning_minute_summary` | append + late-update | History charts |
| Raw event detail | `lightning_events`, `weather_samples` | append-only | Drill-down, audit |
| Ops / quality | `system_events`, `weather_quality_events` | append-only | Health, audit |

## Honest data posture

`lightning_events` is sparse in the current deployment. The Lightning page is **status-first** (noise / disturber / freshness), not deep strike analytics. Empty states are explicit ("no lightning events in this range") rather than misleading empty charts.

## Observability

- Each layer emits structured (JSON) logs.
- Edge logs to local `system_events`, which itself syncs (highest priority) so outages surface on the dashboard.
- Server records every sync run in `sync_runs` and per-(node, table) checkpoints in `sync_cursors`.
- Key metrics: sync lag (`now - last synced ts`), batch error rate, per-stream freshness, batch success rate.

## Tech stack

| Layer | Choice | Reason |
| --- | --- | --- |
| Edge worker | Python 3.11+ | Pi already runs Python; shares the contract package with the server |
| Backend | FastAPI | Strong Pydantic validation on ingest, async reads |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | Mature; heavy time-series queries drop to raw SQL |
| Central DB | PostgreSQL 16 | Constraint; TimescaleDB optional later |
| Frontend | Next.js 14 + TypeScript + TanStack Query | Clean read-API caching |
| Charts | Apache ECharts | Handles dense time-series, zoom, downsample |
| UI | Tailwind + shadcn/ui | Fast, consistent cards / badges / tables |
| Deploy | docker-compose + nginx + Cloudflare Tunnel | Single-host lab deploy; TLS at the Cloudflare edge, no public IP |

## Roadmap

- **Phase 1 (MVP):** contracts + central schema; ingest for `weather_minute_summary` + `system_events`; edge worker for those two; read API `health/latest`, `weather/latest`, `weather/history`; Overview page. Exit: Pi data visible on the server Overview, survives a disconnect.
- **Phase 2:** sync `weather_samples` + `weather_quality_events`; downsampling, wind-rose; Weather History page + CSV export.
- **Phase 3:** sync `lightning_*`; Lightning (status-first), Health, Quality pages; `/ingest/runs`, sync-lag monitoring.
- **Phase 4:** dashboard auth, rate limiting, alerting; TimescaleDB + retention if needed; hooks for anomaly detection and lightning risk scoring.

## AI-ready notes

- `weather_samples.raw_json` preserves the full sensor payload for future ML features.
- Minute summaries give clean, regular time-series for forecasting baselines.
- `system_events` + `weather_quality_events` provide labeled anomaly/quality signals.
- A future alerting/scoring service can read PostgreSQL without touching ingest or the dashboard.
