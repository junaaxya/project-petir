# PetirDashboard

Weather + lightning monitoring system. Arduino sensors → Raspberry Pi edge (SQLite) → PUSH sync → lab server (PostgreSQL + FastAPI + Next.js dashboard).

## Quick Start (Development)

```bash
# Server (FastAPI)
cd server
python -m venv .venv && source .venv/bin/activate
pip install -e . -e ../packages/contracts
alembic upgrade head
uvicorn app.main:app --reload

# Edge sync worker
cd edge
python -m venv .venv && source .venv/bin/activate
pip install -e . -e ../packages/contracts
python -m sync_worker.run

# Web dashboard
cd web
npm install
npm run dev
```

## Production Deployment

```bash
cp .env.example .env
# Edit .env with real credentials and domain

docker compose up -d
```

This brings up:
- **PostgreSQL 16** — central data store
- **FastAPI server** — ingest (write) + query (read) APIs
- **Next.js dashboard** — weather, lightning, health, quality pages

Public access on the lab server is handled by the existing **nginx + Cloudflare
Tunnel** (no public IP, TLS terminated at Cloudflare). See
[docs/nginx-cloudflare.md](docs/nginx-cloudflare.md). Compose only exposes the
app ports (`8000`, `3000`) on the host for nginx to proxy.

## Architecture

```
┌─────────────┐     PUSH      ┌──────────────────┐
│ Raspberry Pi │ ──────────── │    Lab Server     │
│  (SQLite)    │  sync-batch  │  PostgreSQL       │
│  edge worker │              │  FastAPI          │
└─────────────┘              │  Next.js          │
                              └────────┬─────────┘
                                       │
                          nginx + Cloudflare Tunnel
                              (TLS at CF edge)
                                       │
                                   Browser
```

- **Edge** initiates all sync (PUSH only). Server never queries the Pi.
- **Contract-first**: `packages/contracts/` is the shared wire format truth.
- **Clock-independent cursors**: edge_id (append) + change_seq (summary) + db_epoch (reflash detection).
- **Public access**: nginx on the lab host proxies to the containers; a Cloudflare Tunnel exposes it without a public IP. See [docs/nginx-cloudflare.md](docs/nginx-cloudflare.md).

## Project Structure

```
packages/contracts/   Shared wire contract (JSON Schema + Pydantic + TS)
edge/                 Raspberry Pi: sync worker + migrations + systemd
server/               FastAPI: ingest (write) + query (read) + Alembic
web/                  Next.js 14 dashboard
scripts/              Edge bootstrap + systemd install helpers
docs/                 Architecture, sync, API contract, data model, build plan
```

## API Endpoints

### Ingest (write-path, node-token auth)
- `POST /api/ingest/sync-batch` — receive sync envelope from edge
- `GET /api/ingest/runs` — list sync runs

### Query (read-path, optional dashboard-key auth)
- `GET /api/weather/{latest,history,quality-events}`
- `GET /api/lightning/{latest,history,events}`
- `GET /api/system/{events,summary}`
- `GET /api/health/latest`

## Testing

```bash
# Contracts
cd packages/contracts && pytest

# Server (requires Postgres on localhost:55433)
cd server && pytest

# Edge
cd edge && pytest

# Web
cd web && npm run build
```

## Edge Deployment (Raspberry Pi)

See [docs/edge-deploy.md](docs/edge-deploy.md) for full instructions.

```bash
scp -r edge/ scripts/ packages/contracts/ pi@raspberrypi:/tmp/petir-deploy/
ssh pi@raspberrypi 'cd /tmp/petir-deploy && bash scripts/bootstrap-edge.sh'
```

## Documentation

- [Architecture](docs/architecture.md)
- [Sync Protocol](docs/sync.md)
- [API Contract](docs/api-contract.md)
- [Data Model](docs/data-model.md)
- [Build Plan](docs/build-plan.md)
- [Edge Deploy](docs/edge-deploy.md)
- [Edge Migration](docs/edge-migration.md)
- [Edge Schema Drift & First-Sync Safety](docs/edge-schema-drift.md)
- [nginx + Cloudflare Tunnel](docs/nginx-cloudflare.md)
- [Deployment Topology — Pi ↔ Lab Server (no public IP)](docs/deployment-topology.md)
- [Production Checklist](docs/production-checklist.md)
