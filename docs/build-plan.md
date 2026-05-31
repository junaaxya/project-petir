# PetirDashboard — Build Plan

End-to-end implementation plan. Authoritative design is in the other `docs/`; this file is the execution roadmap. Rules of engagement are in [`AGENTS.md`](../AGENTS.md).

## Status legend

- [x] done & verified
- [ ] not started
- [~] in progress

## Phase map

| Phase | Goal | Steps | Outcome |
| --- | --- | --- | --- |
| 0 | Foundation | contracts + docs | Wire format locked; edge & server can go parallel |
| 1 | MVP data flow | 1-6 | Live Pi data reaches server Overview, survives disconnect |
| 2 | Weather history | 7-9 | History charts + CSV export |
| 3 | Lightning + health + audit | 10-13 | Status-first lightning, health, quality pages |
| 4 | Hardening + AI-ready | 14-16 | Auth, infra, retention, ML hooks |

Edge (steps 3-5) and server (steps 1-2) proceed **in parallel** — the contract is locked.

## Live-system safety (read first)

There is an **existing, running** edge system on the Raspberry Pi at `/home/pi/weather-edge` (live SQLite at `/home/pi/weather-edge/data/db/weather_edge.db`) with `weather-ingest` / `lightning-ingest` services and existing health/export/backup timers. This plan is **additive**:

- The sync worker is a **new, separate** unit. It must **not** replace, restart, or modify the existing ingest services during initial rollout.
- All edge DB changes are **additive and idempotent** (new tables, new nullable columns, new triggers). No drops, no renames, no rewrites of the ingestion writer.
- The live schema is **assumed unknown** until inspected on the Pi. Step 4 begins by reading the actual schema, not by trusting this repo's assumptions.
- Always back up the SQLite DB before applying any migration. Every migration has a documented rollback.

---

## Phase 0 — Foundation [x] DONE

- [x] `packages/contracts/schema` — envelope, enums, version, 6 row schemas (JSON Schema truth)
- [x] `packages/contracts/python/petir_contracts` — Pydantic v2 models
- [x] `packages/contracts/ts/index.ts` — TS types for web
- [x] `packages/contracts/tests` — 6 contract tests passing (schema↔Pydantic drift guard)
- [x] `docs/{architecture,sync,api-contract,data-model}.md`
- [x] `AGENTS.md`

Verified: `pytest packages/contracts/tests` → 6 passed.

---

## Phase 1 — MVP data flow

### Step 1 — Server schema (models + Alembic) [ ]

Files: `server/app/models/{registry,weather,lightning,ops}.py`, `server/app/db.py`, `server/app/settings.py`, `server/alembic/{env.py,versions/0001_initial.py}`, `server/pyproject.toml`, `server/alembic.ini`.

Tasks:
- ORM for 3 registry tables: `edge_nodes`, `sync_runs`, `sync_cursors`.
- ORM for 6 data tables with `node_id`, `db_epoch`, `synced_at_utc`, `ingest_run_id`.
- Keys: append -> `UNIQUE (node_id, db_epoch, edge_id)`; summary -> `PK (node_id, minute_utc, source, device)`.
- Indexes per `docs/data-model.md` (node+ts, minute desc, level+ts).
- Alembic initial migration, reversible.

Exit: `alembic upgrade head` then `downgrade base` both clean. 3 registry + 6 data tables created. `pytest server/tests/unit` (model import/metadata) green.

Agent: `ultrabrain` (schema correctness, key/index design).

### Step 2 — Server ingest write-path [ ]

Files: `server/app/ingest/{router,service,upserts,auth}.py`, `server/app/main.py`, `server/app/schemas/ingest.py`, tests under `server/tests/{integration,contract}`.

Tasks:
- `POST /api/ingest/sync-batch`: bearer node-token auth -> contract-version check (426 on major mismatch) -> Pydantic validate envelope -> per-row upsert -> compute `accepted_cursor` -> update `sync_cursors` + `sync_runs` + `edge_nodes.last_seen_utc`, all in one transaction.
- `db_epoch` change detection -> reset cursors for that (node, table).
- Per-row quarantine -> `rejected[]`, cursor still advances.
- `GET /api/ingest/runs` (telemetry read).
- Strict per-node rate limit / 429 backpressure (basic).

Exit (tested):
- Idempotent: same batch twice -> no dupes, same `accepted_cursor`.
- Cursor advances correctly for append (edge_id) and summary (change_seq).
- Poison row quarantined, cursor passes it.
- New `db_epoch` resets cursor.
- Contract test: real `petir_contracts` payloads accepted.

Agent: `ultrabrain`.

### Step 3 — Edge sync worker (single-run, additive) [ ] — parallel with 1-2

Files: `edge/sync_worker/{run,config,cursors,readers,tables,client,run_record}.py`, `edge/systemd/{petir-sync.service,petir-sync.timer}`, `edge/pyproject.toml`, tests under `edge/tests/{unit,integration}`.

**Additive rule:** this worker only reads the existing data tables and writes its own cursor/run bookkeeping. It must not touch the `weather-ingest` / `lightning-ingest` services.

Tasks:
- Local SQLite cursor table read/advance; `db_epoch` + `pi_id` in `meta`.
- Per-table incremental readers (append by id, summary by change_seq).
- `tables.py`: priority order + strategy config.
- `client.py`: httpx POST with bounded retry/backoff, stores server `accepted_cursor` verbatim.
- `run.py`: single-run lifecycle, local `sync_runs`, exit codes (0/1/2).
- systemd oneshot service + timer (`OnUnitActiveSec=15s`).

Exit (tested):
- Unit: cursor advance, reader queries, priority order.
- Integration vs mock server: full run pushes in priority order, advances cursors on ACK, resumes after a simulated 5xx, quarantine-safe.

Agent: `implementation` (+ `executor` for integration harness).

### Step 4 — Live Pi migration & compatibility [ ]

Target: the running edge DB at `/home/pi/weather-edge/data/db/weather_edge.db`. **Additive and idempotent only.** The actual schema is unknown until inspected.

Files: `edge/migrations/{0001_meta_sync_state.sql,0002_summary_change_seq.sql}`, `edge/migrations/apply.py` (idempotent runner + backup), `edge/migrations/inspect.py` (dump live schema), `docs/edge-migration.md`.

Tasks:
1. **Inspect first.** `inspect.py` dumps the live `sqlite_master` schema and column lists for the 6 tables. The migration adapts to what is actually there; it does not assume this repo's column names.
2. **Backup.** `apply.py` copies the DB file (timestamped) before any change; refuses to run without a successful backup.
3. **`meta` table.** Create if absent; insert `pi_id` (stable hardware id) and `db_epoch` (UUID, generated once) if not present.
4. **`sync_state` table.** Create the local cursor table (`table_name`, `last_edge_id`, `last_change_seq`, `last_acked_at`, `rows_sent`).
5. **`change_seq` rollout** on `weather_minute_summary` + `lightning_minute_summary`:
   - `ALTER TABLE ... ADD COLUMN change_seq INTEGER` (nullable; no rewrite).
   - Create `change_seq_counter` table.
   - Backfill existing rows deterministically by `(minute_utc, source, device)` order so current data gets monotonic seqs.
   - Install AFTER INSERT / AFTER UPDATE triggers (guarded against self-refire) per `docs/sync.md`.
6. **Verification queries** confirming triggers fire, `change_seq` strictly increases on update, row counts unchanged.
7. **Rollback** documented per migration (drop triggers, drop `sync_state`/`meta`, drop `change_seq_counter`) — never touches data-table rows.

Exit (tested on a copy of a representative SQLite, not the live DB):
- Re-running `apply.py` is a no-op (idempotent).
- Backfill + trigger gives every summary row a unique, monotonic `change_seq`.
- An UPDATE to an old minute bumps its `change_seq` above all earlier values.
- Ingestion-writer behavior unchanged (a writer-simulation test inserts/updates as the live services would).

Agent: `ultrabrain` (data-safety critical) + `executor` (harness on sample DB).

### Step 5 — Edge deployment-readiness (Raspberry Pi) [ ]

Files: `edge/.env.example`, `docs/edge-deploy.md`, `scripts/bootstrap-edge.sh`, `scripts/install-edge-systemd.sh`.

Tasks:
- `edge/.env.example`: `SERVER_URL`, `NODE_ID`, `NODE_TOKEN`, `EDGE_DB_PATH=/home/pi/weather-edge/data/db/weather_edge.db`, batch sizes, timer interval, log level. No real secrets.
- `scripts/bootstrap-edge.sh`: create venv under `/opt/petir/edge` (uv), install the edge package + `packages/contracts`, run migration `apply.py` (with backup), validate `.env`. Idempotent; safe to re-run.
- `scripts/install-edge-systemd.sh`: copy `petir-sync.{service,timer}` into systemd, `daemon-reload`, enable + start the **timer only**. Explicitly does **not** stop or alter `weather-ingest` / `lightning-ingest`.
- `docs/edge-deploy.md`: step-by-step Pi rollout — prerequisites, backup, bootstrap, migration, dry-run (`python -m sync_worker.run` once), enable timer, verify on server Health page, rollback procedure.

Exit: on a clean test host, following `edge-deploy.md` produces a working timer that completes one sync run with exit 0 against a mock/staging server. Existing-services-untouched check documented.

Agent: `implementation` (+ `writing` for `edge-deploy.md`).

### Step 6 — E2E data flow [ ]

Files: `docker-compose.yml` (postgres + server), `server/tests/e2e/test_pi_to_pg.py` (or scripted harness).

Tasks:
- Spin Postgres + server, run edge worker against a seeded SQLite (post-migration), assert rows land in PG.
- Disconnect simulation: stop server mid-stream, restart, confirm no loss / no dupes and cursor catches up.

Exit: Pi->server->PG verified; survives a disconnect with exactly-stored-once semantics.

Agent: `executor`.

---

## Phase 2 — Weather history

### Step 7 — Read API: weather [ ]

Files: `server/app/query/{weather,downsample,freshness}.py`, `server/app/schemas/query.py`.

Tasks:
- `GET /api/weather/latest`, `/api/weather/history` (interval raw/1m/5m/15m/1h), `/api/weather/quality-events`.
- Downsample bucket SQL builder; raw-range guard (416).
- `GET /api/health/latest` (freshness + sync lag).

Exit: history/latest/health tested; downsample bucket SQL unit-tested; empty range -> 200 `series:[]`.

Agent: `implementation`.

### Step 8 — Frontend Overview [ ]

Files: `web/` scaffold (Next 14, TanStack Query, Tailwind/shadcn, ECharts), `web/src/app/{layout,page}.tsx`, `web/src/components/{common,overview}/*`, `web/src/lib/{api,types}.ts`, `web/src/hooks/*`.

Tasks:
- Global node + time-range filter.
- Overview: metric cards (temp/humidity/pressure/rain/wind), lightning + health badges, 24h temp/humidity mini-chart.
- Typed API client importing `packages/contracts/ts`.

Exit: Overview renders from live API; `npm run build` clean.

Agent: `visual-engineering` (skills: `frontend-ui-ux`).

### Step 9 — Weather History page [ ]

Files: `web/src/app/weather/page.tsx`, `web/src/components/weather/*`. Also extend ingest/edge table configs to sync `weather_samples` + `weather_quality_events`.

Tasks: temp band chart, humidity/pressure/illuminance lines, rain bars, wind-rose, history table + CSV export.

Exit: charts render real history; CSV export works; `npm run build` clean.

Agent: `visual-engineering`.

---

## Phase 3 — Lightning + health + audit

Lightning stays **status-first** and honest about sparse event data — no charts that imply richness the data does not have; explicit empty-states.

### Step 10 — Read API: lightning + system [ ]

Files: `server/app/query/{lightning,system}.py`. Extend ingest/edge to sync `lightning_*`.

Tasks: `/api/lightning/{latest,history,events}`, `/api/system/summary`.

Exit: endpoints tested; honest empty handling for sparse events.

Agent: `implementation`.

### Step 11 — Lightning page (status-first) [ ]

Files: `web/src/app/lightning/page.tsx`, `web/src/components/lightning/*`.

Tasks: big status badge, last-event card, activity timeline (count/disturber/noise), events table with explicit empty-state. No misleading charts on sparse data.

Exit: renders; empty-state honest; `npm run build` clean.

Agent: `visual-engineering`.

### Step 12 — Health page [ ]

Files: `web/src/app/health/page.tsx`, `web/src/components/health/*`.

Tasks: per-stream freshness table, sync-lag chart, node status, recent `system_events`, batch success rate (from `/api/ingest/runs`).

Exit: renders from health + runs API.

Agent: `visual-engineering`.

### Step 13 — Data Quality / Audit page [ ]

Files: `web/src/app/quality/page.tsx`, `web/src/components/quality/*`.

Tasks: quality events table (filter by status/reason), valid/warn/invalid distribution, raw sample drill-down.

Exit: renders from quality-events API.

Agent: `visual-engineering`.

---

## Phase 4 — Hardening + AI-ready

### Step 14 — Auth + rate limiting [ ]

- Dashboard-user auth on read-path (`verify_dashboard_user`).
- Tighten per-node write rate limiting; token rotation support in `edge_nodes`.

### Step 15 — Infra [ ]

Files: `docker-compose.yml` (postgres + server + web), `docs/nginx-cloudflare.md`, `.env.example`, `README.md`.

Exit: `docker compose up` brings up postgres + server + web; nginx + Cloudflare Tunnel (host) expose it publicly with TLS at the Cloudflare edge.

### Step 16 — AI-ready + retention [ ]

- TimescaleDB hypertables if volume warrants; retention/prune policy.
- Hooks for anomaly detection, lightning risk scoring (read-only consumer of PG, separate from ingest/dashboard).

---

## Cross-cutting verification gates

Every step is "done" only when:
- Package test suite passes (`pytest` for py, `npm run build` for web).
- Schema changes: Alembic up **and** down clean. Edge migrations: idempotent re-run + documented rollback, tested on a DB copy.
- New behavior has a test; no test deleted to pass.
- `lsp_diagnostics` clean on changed files.
- Stated what was verified vs not.

## Parallelization

- Phase 1: steps 1-2 (server) || step 3 (edge). Steps 4-5 follow step 3 (edge migration + deploy). Step 6 joins server + edge.
- Phase 2-3: each read-API step precedes its frontend page; frontend pages are independent of each other and can be parallel once their API exists.
