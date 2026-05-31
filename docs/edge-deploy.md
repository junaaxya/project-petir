# Edge Deployment — Raspberry Pi

How to roll out the PetirDashboard sync worker on the **live** Raspberry Pi. The rollout is **additive**: it adds a single-run sync job on a systemd timer and never replaces, restarts, or modifies the running `weather-ingest` / `lightning-ingest` services.

> Build and test happen on the laptop. These steps run on the Pi only at deploy time. Test the migration on a **copy** of the DB first (see [edge-migration.md](./edge-migration.md)).

## Prerequisites

- Pi reachable over the network to the lab server (`SERVER_URL`).
- The node is registered in the server's `edge_nodes` table with a token hash; you hold the matching `NODE_TOKEN`.
- Python 3.11+ on the Pi. `uv` is preferred but optional (the bootstrap falls back to `venv` + `pip`).
- The repo (or at least `edge/`, `packages/contracts/`, `scripts/`) available on the Pi.

## What gets installed

- A venv inside the clone at `<repo>/edge/.venv` (override with `PETIR_EDGE_PREFIX`) with `petir-edge` + `petir-contracts`. The dashboard build toolchain (Node, web) is **not** installed — the edge stays lightweight.
- Additive DB objects: `meta`, `sync_state`, `change_seq` + triggers (see [edge-migration.md](./edge-migration.md)).
- `petir-sync.service` (Type=oneshot) + `petir-sync.timer` (`OnUnitActiveSec=15s`). The service unit is **generated** by `install-edge-systemd.sh` from this machine's real layout (service user = the invoking sudo user, e.g. `pi`; paths = the clone). No `/opt` or special-user assumptions.

## Steps

### 1. Configure

```bash
cp edge/.env.example edge/.env
# edit edge/.env: SERVER_URL, NODE_ID, NODE_TOKEN, EDGE_DB_PATH
```

`EDGE_DB_PATH` points at the live DB: `/home/pi/weather-edge/data/db/weather_edge.db`.

### 2. Inspect the live schema (read-only)

```bash
cd edge
python -m migrations.inspect /home/pi/weather-edge/data/db/weather_edge.db
```

Confirm the summary tables and their columns match expectations before migrating.

### 3. Bootstrap (venv + install + backup + migrate + dry-run)

```bash
scripts/bootstrap-edge.sh
```

This creates the venv, installs the packages, validates `.env`, runs the **backup-first** migration (`apply.py` writes `weather_edge.db.backup-<timestamp>`), and performs one dry-run sync cycle. The dry-run exit code is informational: `0` ok, `1` partial, `2` failed.

### 4. Install and enable the timer

```bash
sudo scripts/install-edge-systemd.sh
```

Installs the units, reloads systemd, and enables + starts **only** `petir-sync.timer`. It does not touch the ingest services.

### 5. Verify

```bash
# trigger one run immediately
sudo systemctl start petir-sync.service
journalctl -u petir-sync.service -n 50 --no-pager

# timer schedule
systemctl list-timers petir-sync.timer --no-pager

# confirm the ingest services are still running and untouched
systemctl is-active weather-ingest.service lightning-ingest.service
```

On the server, confirm data is arriving: the dashboard Health page (or `GET /api/ingest/runs`) should show recent runs for this `NODE_ID` with advancing cursors.

## Rollback

Stop the new timer (the existing ingest services are unaffected):

```bash
sudo systemctl disable --now petir-sync.timer
```

To remove the units entirely:

```bash
sudo rm -f /etc/systemd/system/petir-sync.service /etc/systemd/system/petir-sync.timer
sudo systemctl daemon-reload
```

To revert the additive DB objects, follow the rollback section in [edge-migration.md](./edge-migration.md). The `change_seq` column is nullable and safe to leave in place; a full revert restores the timestamped backup created during bootstrap.

## Operational notes

- The worker is single-run: each timer tick runs one cycle and exits. There is no long-lived daemon.
- The cursor only advances after a 2xx ACK, so a server outage simply pauses progress; the next tick resumes from the last checkpoint.
- Logs: `journalctl -u petir-sync.service`. Each run also writes a row to the local `sync_runs` table in the edge DB.
