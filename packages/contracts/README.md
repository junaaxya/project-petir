# petir-contracts

Shared wire contract for the PetirDashboard edge to server sync protocol. This package is the single source of truth for everything that crosses the network between the Raspberry Pi edge node and the lab server.

The edge sync worker and the server ingest layer both depend on this package. **Neither imports the other** — they only share this contract. This is the decoupling boundary.

## Layout

| Path | Role | Consumed by |
| --- | --- | --- |
| `schema/` | Language-neutral truth (JSON Schema 2020-12) | contract tests, codegen |
| `schema/envelope.json` | `POST /api/ingest/sync-batch` request body | edge + server |
| `schema/enums.json` | All allowed enum values | edge + server + web |
| `schema/rows/*.json` | Per-table row shapes | edge + server |
| `schema/version.json` | Contract semver | release process |
| `python/petir_contracts/` | Pydantic v2 models | edge worker + server ingest |
| `ts/index.ts` | TypeScript types | web dashboard |
| `tests/` | Schema validation + example round-trips | CI |

## Versioning

Semver on `CONTRACT_VERSION`:

- **MAJOR** — breaking change. Server rejects mismatched MAJOR with HTTP `426`.
- **MINOR** — adds optional fields, backward compatible.
- **PATCH** — docs / non-structural.

The server validates **MAJOR equality only**. An edge on `1.x` talks to a server on `1.y` fine; a `2.x` edge against a `1.x` server is refused.

## Cursor model (why two strategies)

- **append** tables (`weather_samples`, `lightning_events`, `weather_quality_events`, `system_events`) carry `edge_id` (SQLite autoincrement). Cursor = `last_edge_id`. Monotonic, never reused under single-writer.
- **summary** tables (`weather_minute_summary`, `lightning_minute_summary`) carry `change_seq` (bumped by an edge trigger on every insert/update). Cursor = `last_change_seq`. This is what prevents silent loss of late updates to old minutes.

`db_epoch` (UUID) is sent on every envelope. A new `db_epoch` for a node tells the server the edge DB was reflashed, so cursors reset instead of silently overwriting unrelated history. See `docs/sync.md`.

## Local install

```bash
pip install -e packages/contracts          # runtime
pip install -e "packages/contracts[test]"  # with test deps
pytest packages/contracts/tests
```
