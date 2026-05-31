# Edge Migration — Live Raspberry Pi

How to additively prepare the **live** edge SQLite DB at `/home/pi/weather-edge/data/db/weather_edge.db` for the sync worker. This is **data-safety critical**. The migration is additive and idempotent: it adds new tables, a nullable column, and triggers. It never drops, renames, or rewrites existing tables, and it does not touch the running `weather-ingest` / `lightning-ingest` services.

> Test on a **copy** first. Never run an untested migration against the live DB.

## What it does

1. `meta` table — stores `pi_id` (stable id) and `db_epoch` (UUID, generated once; identifies this DB generation so the server can detect a reflash).
2. `sync_state` table — the edge-local cursor (`last_edge_id` / `last_change_seq` per table).
3. `change_seq` on the two summary tables (`weather_minute_summary`, `lightning_minute_summary`):
   - adds a nullable `change_seq INTEGER` column (no table rewrite),
   - creates `change_seq_counter`,
   - backfills existing rows with deterministic monotonic seqs ordered by `(minute_utc, source, device)`,
   - installs AFTER INSERT / AFTER UPDATE triggers that bump `change_seq` on every write.

### Why the ordering matters

Backfill runs **before** the triggers are created. If the triggers existed first, the backfill `UPDATE`s would recursively fire the counter and produce inconsistent seqs. The counter is set to the backfilled max so the live triggers continue from there. The `AFTER UPDATE` trigger is guarded with `WHEN NEW.change_seq IS OLD.change_seq` so it does not re-fire on its own write.

## Files

- `edge/migrations/inspect.py` — read-only: dumps schema, columns, triggers, row counts. Run this first.
- `edge/migrations/0001_meta_sync_state.sql` — `meta` + `sync_state` (pure `IF NOT EXISTS`).
- `edge/migrations/0002_summary_change_seq.sql` — counter + triggers (`IF NOT EXISTS`).
- `edge/migrations/apply.py` — backup-first idempotent runner (handles the non-idempotent ADD COLUMN + backfill with guards).

## Procedure (on the Pi, at deploy time)

```bash
# 1. Inspect the live schema FIRST (read-only). Confirm column names match expectations.
python -m migrations.inspect /home/pi/weather-edge/data/db/weather_edge.db

# 2. Apply (takes a timestamped backup automatically; refuses to run without one).
python -m migrations.apply /home/pi/weather-edge/data/db/weather_edge.db

# 3. Re-inspect to confirm meta, sync_state, change_seq, and the 4 triggers exist.
python -m migrations.inspect /home/pi/weather-edge/data/db/weather_edge.db
```

`apply.py` writes a backup next to the DB as `weather_edge.db.backup-<UTC timestamp>` before any change.

## Idempotency

Re-running `apply.py` is a no-op: `meta`/`sync_state`/`change_seq_counter`/triggers use `IF NOT EXISTS`, the column is only added if missing, and backfill only touches rows where `change_seq IS NULL`. A second run reports `added_column: []` and `backfilled: {...: 0}`.

## Verification (run on a copy)

The migration is covered by `edge/tests/test_migration.py`:

- adds meta / sync_state / 4 triggers,
- backup is created,
- backfill is monotonic and unique,
- re-run is idempotent (no duplicate rows, no re-backfill),
- a new INSERT gets the next `change_seq`,
- an UPDATE to an old row bumps its `change_seq` above all existing values,
- row counts unchanged (writer behavior preserved),
- empty summary tables handled.

```bash
cd edge && . .venv/bin/activate
pytest tests/test_migration.py -q
```

## Rollback

The migration only adds objects; rolling back removes them and leaves all data rows intact.

```sql
DROP TRIGGER IF EXISTS wms_change_seq_ins;
DROP TRIGGER IF EXISTS wms_change_seq_upd;
DROP TRIGGER IF EXISTS lms_change_seq_ins;
DROP TRIGGER IF EXISTS lms_change_seq_upd;
DROP TABLE IF EXISTS change_seq_counter;
DROP TABLE IF EXISTS sync_state;
DROP TABLE IF EXISTS meta;
```

The `change_seq` column can be left in place (it is nullable and harmless). SQLite cannot drop a column without a table rebuild; dropping it is **not** recommended on the live DB. If a full revert is required, restore the timestamped backup created by `apply.py`:

```bash
cp /home/pi/weather-edge/data/db/weather_edge.db.backup-<stamp> \
   /home/pi/weather-edge/data/db/weather_edge.db
```

Stop the sync timer before restoring (`systemctl stop petir-sync.timer`); never restore while the ingest services are mid-write — coordinate a brief quiet window.
