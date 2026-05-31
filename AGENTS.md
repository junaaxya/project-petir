# AGENTS.md

Authoritative rules-of-engagement for AI/coding agents working on **PetirDashboard**. Read this before touching code. The full design lives in [`docs/`](./docs); the execution roadmap lives in [`docs/build-plan.md`](./docs/build-plan.md). This file is the guardrails.

## What this project is

Weather + lightning monitoring. Arduino sensors → Raspberry Pi edge (SQLite) → **PUSH** sync → lab server (PostgreSQL + FastAPI + Next.js dashboard).

Read the full design: [architecture](./docs/architecture.md) · [sync](./docs/sync.md) · [api-contract](./docs/api-contract.md) · [data-model](./docs/data-model.md).

## Workflow & machine roles

These three roles are **not** equal build machines. Do not conflate them.

- **User's laptop — the active development machine.** All coding, dashboard build, and test workflows happen here. This is where the agent runs. When in doubt, assume a command runs on the laptop.
- **Raspberry Pi — live sensor-data source, future edge runtime.** It already holds the live data and will later run the edge sync worker / edge API so production can pull from it. It is **not** a development machine and must not be assumed reachable for routine dev commands.
- **Lab server — future production deploy target.** Will host the central PostgreSQL, the API, and the served dashboard. It is **not** the current build environment.

Build and test on the laptop. Deploy the edge to the Pi and the stack to the lab server as explicit, separate steps.

## Current deployment reality

The Raspberry Pi already runs a live `weather-edge` system. Treat it as production:

- SQLite DB: `/home/pi/weather-edge/data/db/weather_edge.db`.
- Running services: `weather-ingest.service`, `lightning-ingest.service`.
- Existing health / export / backup timers are already in place.
- The new edge sync / edge API rollout is **additive in Phase 1**. It must **not** replace, restart, or modify the current ingest pipeline unless a migration task explicitly says so.
- Schema additions (`meta`, `sync_state`, summary `change_seq`) must be introduced **compatibly**: new tables, new nullable columns, new triggers — backed up first, idempotent, with a documented rollback. Inspect the live schema before migrating; never assume column names from this repo.

## Non-negotiable decisions

Load-bearing. Do not violate.

1. **Contract-first.** `edge/` and `server/` must **never import each other**. The only shared truth is `packages/contracts`. To change the wire format, edit the contract (schema + Python + TS together) and bump `CONTRACT_VERSION`.
2. **PUSH only.** The Pi initiates all sync. The server **never** live-queries the Pi SQLite.
3. **Clock-independent cursors.**
   - Append (event) tables use an **edge-local monotonic sequence** — the SQLite autoincrement `edge_id`.
   - Summary (late-updated) tables use **`change_seq`**, produced by an additive trigger (or equivalent monotonic mechanism) bumped on every insert/update.
   - **Timestamp-based cursors are forbidden** — they silently lose late updates and break under clock skew.
   - The edge **persists the server's `accepted_cursor` verbatim**; it never computes its own. See [sync.md](./docs/sync.md).
4. **`db_epoch` on every envelope.** A new `db_epoch` means the edge DB was reflashed; the server resets cursors. Do not drop this field.
5. **Single-run sync worker.** `python -m sync_worker.run` runs once and exits, scheduled by a systemd timer. Do **not** turn it into a long-lived daemon.
6. **Write/read path separation.** `server/app/ingest/` (node-token, write-only) and `server/app/query/` (read-only) share no auth and no service code.
7. **Idempotent upsert + quarantine.** All ingest is `ON CONFLICT` upsert. A bad row goes into `rejected[]` and the cursor still advances past it; one poison row must never block a stream.
8. **Additive edge rollout.** The sync worker is **new and separate** from the live ingest services and must not replace, restart, or modify them during Phase 1. All edge DB migrations are additive and idempotent. See [Current deployment reality](#current-deployment-reality) and [build-plan.md](./docs/build-plan.md) steps 4-5.
9. **Edge stays lightweight.** Edge deployment on the Pi must remain minimal — sync worker plus its dependencies only. The Pi must **not** require the dashboard build toolchain (Node, web build, etc.) during normal development. Keep heavy work on the laptop.
10. **Honest lightning UI.** Lightning event data is sparse. UI must stay **status-first** (status badge, last event, freshness) with explicit empty-states. Never render charts that imply richness the data does not have.

## AGENTS.md vs build-plan.md

- **AGENTS.md** = rules-of-engagement + architecture guardrails (this file).
- **[build-plan.md](./docs/build-plan.md)** = execution roadmap (steps, order, exit criteria).
- If they ever diverge, **the AGENTS.md guardrails win** — update the roadmap to match, not the other way around.

## Repository layout

```
packages/contracts/   Shared wire contract (JSON Schema + Pydantic + TS). SOURCE OF TRUTH.
edge/                 Raspberry Pi: single-run sync worker + migrations + systemd units.
server/               FastAPI: app/ingest (write) + app/query (read) + models + alembic.
web/                  Next.js dashboard. Components organized per domain.
docs/                 Architecture, sync, API contract, data model, build plan.
scripts/              Edge bootstrap + systemd install helpers.
```

## Deployment expectations

| Machine | Now | Later |
| --- | --- | --- |
| Laptop (dev) | all coding, web + server build/test, edge dev against a sample DB | — |
| Raspberry Pi | live ingest + SQLite (untouched) | runs the edge sync worker / edge API (additive) |
| Lab server | — | central PostgreSQL + FastAPI + served dashboard (production) |

Expected deploy-support files (kept in the repo, run on the Pi only at deploy time):

- `edge/.env.example`
- `docs/edge-deploy.md`
- `scripts/bootstrap-edge.sh`
- `scripts/install-edge-systemd.sh`

## Per-package conventions

### packages/contracts (Python + JSON + TS)

- `schema/*.json` is the truth. `python/petir_contracts/` and `ts/index.ts` stay in sync with it.
- After any change, run the contract tests; they exist to catch schema/Pydantic drift.

```bash
uv pip install -e "packages/contracts[test]"
pytest packages/contracts/tests
```

### server (Python, FastAPI, SQLAlchemy 2.0, Alembic)

- Validate inbound rows with the Pydantic models from `petir_contracts`. Do not hand-roll parallel schemas.
- Heavy time-series queries may use raw SQL; everything else uses the ORM.
- Every schema change is a reversible Alembic migration.
- Keep ingest and query layers separate.
- Read-path APIs must be **honest about sparse or empty datasets** — return `200` with empty `series`/`items`, never fabricate data.
- Build and test from the laptop.

```bash
cd server
uv venv && uv pip install -e . -e ../packages/contracts
alembic upgrade head
pytest
```

### edge (Python)

- Depends on `petir_contracts`. No server imports.
- In MVP rollout the worker targets the **live SQLite DB** at `/home/pi/weather-edge/data/db/weather_edge.db` (path via `EDGE_DB_PATH`). The rollout is **additive** to the running ingest services.
- The worker is stateless except for its local cursor table; the cursor advances only after a 2xx ACK.
- Develop and test on the laptop against a **copy/sample** SQLite. Do not assume dev commands run on the Pi.

```bash
cd edge
uv venv && uv pip install -e . -e ../packages/contracts
pytest
python -m sync_worker.run   # one cycle; exit code is the signal
```

### web (Next.js 14, TypeScript, TanStack Query, ECharts, Tailwind/shadcn)

- Import types from `packages/contracts/ts`. Do not redefine API shapes.
- Components live under `src/components/<domain>/` (overview, weather, lightning, health, quality, common).
- Read-path only; the frontend knows nothing about the Pi.
- Keep lightning views **status-first and honest** (see non-negotiable #10).
- Build and test from the laptop.

```bash
cd web
npm install
npm run dev
npm run build
```

## Python environment

- Prefer **`uv venv` + `uv pip`** with a local virtual environment on the laptop.
- Do **not** rely on system-wide / global pip.
- On the Raspberry Pi, avoid system-wide installs unless a deployment task explicitly requires it; the edge venv lives under its deploy prefix (e.g. `/opt/petir/edge`).
- Do not assume routine development commands are run directly on the Pi.

## Code style

- **Avoid decorative comments and docstrings.** Prefer self-documenting names. Do not add section-divider or restate-the-code comments. A repo hook flags every comment/docstring — expect to justify or remove it.
- **Keep a comment only when the logic is genuinely non-obvious:** sync/cursor invariants, security boundaries, tricky SQL, retry/quarantine behavior, migration hazards, regex, math, or public contract APIs.
- No type-error suppression: never `# type: ignore`, `as any`, `@ts-ignore`, `@ts-expect-error`.
- No empty `except:` / `catch {}`.
- Match existing patterns in the package you are editing.

## Testing & verification (required before "done")

- File edits → run the package's test suite; it must pass.
- New feature or bugfix → add/extend a test.
- Server schema change → Alembic up **and** down clean.
- Edge migration → idempotent re-run + documented rollback, tested on a **DB copy**, never the live DB.
- State what you verified and what you could not. Never delete a failing test to make a suite pass.

## Build order (summary)

Foundation (`packages/contracts` + `docs`) is **done and verified**. Full steps and exit criteria are in [build-plan.md](./docs/build-plan.md).

- Phase 1 (MVP, steps 1-6): server schema → ingest write-path; in parallel edge worker → live-Pi migration → deploy-readiness; then E2E data flow.
- Phase 2 (7-9): weather read API → Overview → weather history.
- Phase 3 (10-13): lightning + system read API → lightning / health / quality pages.
- Phase 4 (14-16): auth, infra (compose + nginx/Cloudflare Tunnel), AI-ready + retention.

Server and edge run in parallel because the contract is locked.

## Environment notes

- `rm -rf` is blocked by a safety net. Clean up with `find <path> -delete` (after a `-print` preview) or ask the user.
- Laptop dev: Python 3.11+, Node 20+. Production target: PostgreSQL 16.
- All timestamps are UTC ISO-8601 on the wire and `timestamptz` in PostgreSQL.
