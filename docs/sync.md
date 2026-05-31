# PetirDashboard — Sync Design

How field data moves from the Raspberry Pi SQLite buffer to the lab PostgreSQL, incrementally, idempotently, and tolerant of outages. The wire format is defined in [`packages/contracts`](../packages/contracts/README.md).

## Model in one line

The Pi runs a **single-run** sync job on a systemd timer. Each run reads a local cursor per table, selects new rows, POSTs them to the server, and advances the cursor **only after a durable server ACK**. Cursors are monotonic and clock-independent.

## Why not timestamp cursors

Timestamp-based cursors are unsafe on field hardware:

1. **Late updates to summary rows.** A minute row is updated repeatedly while that minute is still being aggregated. A cursor on `updated_at_utc` can pass a minute and then miss a later update to it — the dashboard shows stale values permanently.
2. **Clock skew.** The Pi often has no RTC. NTP can step the clock backward on boot/reconnect. A cursor on `created_at_utc` then produces permanent gaps or stalls.
3. **Reflash / DB reset.** SQLite rowids restart from 1 after a fresh DB. Upserting by `(node_id, edge_id)` would silently overwrite unrelated historical rows.

## The fix — two monotonic strategies + db_epoch

### append strategy (event tables)

`weather_samples`, `lightning_events`, `weather_quality_events`, `system_events`.

These are append-only. The SQLite `INTEGER PRIMARY KEY AUTOINCREMENT` `id` is strictly monotonic and never reused under a single writer. We send it as `edge_id`.

- Cursor field: `last_edge_id`.
- Query: `SELECT * FROM t WHERE id > :last_edge_id ORDER BY id LIMIT :n`.
- Advance to `MAX(edge_id)` among ACKed rows.

### summary strategy (late-updated minute tables)

`weather_minute_summary`, `lightning_minute_summary`.

These rows are updated in place during the minute. A timestamp cursor is unsafe (reason 1 above). Instead each row carries a `change_seq` that is **bumped on every insert or update** by an additive trigger, so a late update to an old minute always gets a higher `change_seq` than its earlier version and is therefore re-sent.

- Cursor field: `last_change_seq`.
- Query: `SELECT * FROM t WHERE change_seq > :last_change_seq ORDER BY change_seq LIMIT :n`.
- Advance to `MAX(change_seq)` among ACKed rows.

Trigger approach is **additive** — it does not modify the existing ingestion writer. Example for `weather_minute_summary` (mirror for lightning):

```sql
ALTER TABLE weather_minute_summary ADD COLUMN change_seq INTEGER;

CREATE TABLE IF NOT EXISTS change_seq_counter (
  table_name TEXT PRIMARY KEY,
  value      INTEGER NOT NULL DEFAULT 0
);

CREATE TRIGGER IF NOT EXISTS wms_change_seq_ins
AFTER INSERT ON weather_minute_summary
BEGIN
  UPDATE change_seq_counter SET value = value + 1 WHERE table_name = 'weather_minute_summary';
  UPDATE weather_minute_summary
     SET change_seq = (SELECT value FROM change_seq_counter WHERE table_name = 'weather_minute_summary')
   WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS wms_change_seq_upd
AFTER UPDATE ON weather_minute_summary
WHEN NEW.change_seq IS OLD.change_seq
BEGIN
  UPDATE change_seq_counter SET value = value + 1 WHERE table_name = 'weather_minute_summary';
  UPDATE weather_minute_summary
     SET change_seq = (SELECT value FROM change_seq_counter WHERE table_name = 'weather_minute_summary')
   WHERE rowid = NEW.rowid;
END;
```

The `WHEN NEW.change_seq IS OLD.change_seq` guard stops the update trigger from re-firing on its own write.

### db_epoch

A UUID stored in the edge `meta` table, regenerated whenever the SQLite DB is initialized or reflashed. It is sent on every envelope.

- The server tracks cursors per `(node_id, table_name)` and remembers the last `db_epoch`.
- If the server sees a **new** `db_epoch` for a node, the edge DB was reset. The server resets cursors for that node so a restarted `edge_id` sequence cannot overwrite unrelated history.

## Sync priority

Push order per run, highest to lowest:

1. `system_events` — small, surfaces outages first.
2. `weather_minute_summary` — drives the dashboard.
3. `lightning_minute_summary` — status.
4. `weather_quality_events` — audit.
5. `lightning_events` — raw, small.
6. `weather_samples` — raw, large; last, may be throttled.

If bandwidth is tight, `weather_samples` can lag without harming Overview/History.

## Run lifecycle (single-run, systemd timer)

```
timer fires (OnUnitActiveSec=15s)
  -> python -m sync_worker.run        # Type=oneshot
       1. run_id = uuid4(); record local sync_run (started)
       2. for table in PRIORITY_ORDER:
            cursor = read_local_cursor(table)
            rows   = read_incremental(table, cursor, limit)
            if not rows: continue
            resp   = client.post_batch(envelope, retry=bounded)
            if resp.ok:
                advance_local_cursor(table, resp.accepted_cursor)
            else:
                record failure; continue or abort per policy
       3. finalize local sync_run (status, rows, duration)
       4. exit(code)   # 0=ok, 1=partial, 2=hard fail
```

Why single-run beats a daemon here:

- **Crash-safe** — no in-memory state to lose; the next timer tick resumes from the cursor.
- **Bounded resources** — nothing long-lived to leak memory on the Pi.
- **Observable** — `systemctl status petir-sync` and per-run `sync_runs` rows tell the whole story; exit code is the signal.
- **Simple backoff** — retries are bounded *within* a run; backoff *between* runs is just the timer interval.

`OnUnitActiveSec` schedules the next tick after the previous run finishes, so runs never overlap and a long backlog naturally lowers frequency.

A daemon would only be justified if push latency must be consistently sub-second. For monitoring, a 15s timer is enough.

## Idempotency and the authoritative cursor

- Every table has a server-side natural key, so ingest is `INSERT ... ON CONFLICT DO UPDATE/NOTHING`. Re-sending a batch is safe.
  - append tables: `UNIQUE (node_id, db_epoch, edge_id)`.
  - summary tables: `PRIMARY KEY (node_id, minute_utc, source, device)`.
- The server returns `accepted_cursor`. **The edge stores that value**, it does not compute its own. If the edge and server ever disagree (e.g. after a reset), the server's cursor wins, making recovery deterministic.
- Upsert of rows + cursor update + run record happen in **one DB transaction**, so a cursor never advances without the data being durable.

## Retry, backoff, backpressure

- Within a run: bounded exponential backoff with jitter (e.g. 2s, 4s, 8s, capped), a few attempts, then the run exits non-zero.
- Between runs: the timer interval is the backoff. No unbounded retry loop.
- Server `429` means slow down: the edge aborts the run early; the next tick is the natural backoff.

## Offline buffering

SQLite is the buffer. While offline, data accumulates and the cursor does not advance. On reconnect the worker drains the backlog in cursor order, one bounded batch per table per run, so it never floods the server.

## Failure and recovery matrix

| Scenario | Within the run | Between runs |
| --- | --- | --- |
| Network down | bounded retry, then exit != 0 | next tick resumes from cursor |
| Server 5xx | do not advance cursor | retry next tick |
| Server 429 | abort run early | next tick (interval = backoff) |
| Per-row 422 | quarantine the row, cursor still advances past it | not stuck |
| Contract 426 | abort, log loudly to local `system_events` | needs a new contract deploy |
| Pi reboot mid-run | run dies; cursor not advanced for un-ACKed batch | next boot timer resumes; upsert is idempotent |
| Edge DB reflash | new `db_epoch` sent | server resets cursors for the node |

## Per-row quarantine

If a single row fails validation the server returns it in `rejected[]` but still advances `accepted_cursor` past it. This prevents one poison row from blocking the stream forever. Rejected rows are logged for later inspection.

## Local edge sync_runs (mirror)

```sql
CREATE TABLE IF NOT EXISTS sync_runs (
  run_id        TEXT PRIMARY KEY,
  started_at    TEXT NOT NULL,
  finished_at   TEXT,
  status        TEXT,            -- ok | partial | failed
  tables_count  INTEGER DEFAULT 0,
  rows_sent     INTEGER DEFAULT 0,
  rows_rejected INTEGER DEFAULT 0,
  exit_code     INTEGER,
  error_detail  TEXT
);
```

This local record also syncs (via `system_events`), so the Health page can compare runs the edge recorded against runs the server received and detect runs lost in transit.
