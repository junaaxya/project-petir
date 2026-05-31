# Real-Pi first sync — schema drift & data-loss safety

The live Raspberry Pi firmware emits values that differ from the original
contract guesses. This was caught by running a **copy** of the real
`weather_edge.db` through the full pipeline before any production sync. This doc
records the drift, the fix, and the exact deploy order that prevents permanent
data loss.

## The quarantine data-loss trap

Ingest is poison-row safe: a row that fails validation goes into `rejected[]`
and **the cursor still advances past it**. That is correct for one bad row in a
stream — but if a *systematic* drift rejects whole tables, the cursor walks past
thousands of valid rows that will never be re-sent. On the Pi the source rows
remain in SQLite, but the edge cursor has moved on. Recovery then needs a
server-side cursor reset (or `db_epoch` bump) to force a full idempotent replay.

Therefore: **never run the first real-Pi sync until the contract matches the
firmware.** Validate on a copy first.

## Drift found (contract v1) and resolution (contract v2)

Verified against a real copy: 110459 source rows, 64519 rejected under v1.

### Enum vocabulary drift — fixed by edge normalization (lexical synonyms)

The edge `sync_worker/normalize.py` maps firmware spellings to contract values
before send. Pure synonyms only; genuinely-new states go in the contract.

| Table.field | Firmware value | Resolution |
| --- | --- | --- |
| weather_minute_summary.status | `healthy` | edge → `ok` |
| system_events.level | `warning` | edge → `warn` |
| lightning_minute_summary.status | `noisy` | edge → `noise` |
| lightning_minute_summary.status | `active` | edge → `activity` |
| lightning_minute_summary.status | `saturated` | **added to contract** (real new state) |

### Type drift — fixed in the contract (str → int)

The firmware stores these as integers; the contract was simply wrong.

| Table.field | v1 | v2 |
| --- | --- | --- |
| weather_samples.wind_dir_code | string | integer (compass sector 0-15) |
| weather_samples.ingest_run_id | string | integer |
| lightning_events.irq_source | string | integer (AS3935 IRQ code) |
| lightning_events.ingest_run_id | string | integer |

Server columns widened to match (`Integer`/`BigInteger`) via Alembic `0004`.
`CONTRACT_VERSION` bumped `1.0.0 → 2.0.0` (str→int is breaking; the server's
major-version gate now refuses any v1 producer).

Re-validated on the copy after the fix: **110459 accepted, 0 rejected.**

## Deploy order (do not reorder 4–7)

1. Land the contract fix (`saturated` + int types), bump to `2.0.0`, run
   `pytest packages/contracts/tests` — must pass.
2. Build/confirm the edge normalize layer and the server migration
   (`alembic upgrade head` to `0004`). Add a per-cycle "rejected > 0" alert.
3. Validate on a **copy** of the live DB until rejected ≈ 0. Gate: do not
   proceed until green. (See `server/scripts/test_real_pi_sync.py`.)
4. Confirm the live Pi is untouched: `sync_state` absent / cursors at zero,
   `weather-ingest` / `lightning-ingest` still running.
5. Deploy the **server v2 first** — its major gate now rejects any v1 producer
   (intentional).
6. Deploy the **edge v2** to the Pi (worker + normalize + contracts only). Do
   **not** enable the timer yet.
7. Enable the `petir-sync.timer` for the first real sync. Cursors start at zero,
   so the full history ingests cleanly. Watch the first cycle's accepted/rejected
   counts.

## Recovery net

Source rows persist on the Pi SQLite and ingest is idempotent `ON CONFLICT`
upsert, so a server cursor reset (or `db_epoch` bump) forces a safe full replay
with no duplicates. Permanent loss requires two simultaneous failures: unnoticed
drift advancing the cursor **and** the Pi pruning those rows before a reset. The
rejected-count alert from step 2 is the tripwire that prevents the first.
