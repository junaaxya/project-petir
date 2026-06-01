from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import datetime, timezone

from petir_contracts import CONTRACT_VERSION, CursorStrategy

from sync_worker import cursors, readers, run_record
from sync_worker.client import (
    BackpressureError,
    FatalBatchError,
    RetriableError,
    SyncClient,
)
from sync_worker.config import Config, load_config
from sync_worker.tables import PRIORITY_ORDER, TableConfig

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_FAILED = 2


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        + "Z"
    )


def _build_envelope(
    config: Config,
    db_epoch: str,
    run_id: str,
    cfg: TableConfig,
    cursor_value: int,
    rows: list[dict],
    sequence: int,
) -> dict:
    if cfg.strategy is CursorStrategy.append:
        cursor = {"strategy": "append", "last_edge_id": cursor_value}
    else:
        cursor = {"strategy": "summary", "last_change_seq": cursor_value}
    return {
        "contract_version": CONTRACT_VERSION,
        "node_id": config.node_id,
        "db_epoch": db_epoch,
        "run_id": run_id,
        "run": {"started_at_utc": _now_iso(), "sequence": sequence},
        "table": cfg.name,
        "cursor": cursor,
        "rows": rows,
    }


def _accepted_value(response_cursor, strategy: CursorStrategy) -> int | None:
    if strategy is CursorStrategy.append:
        return response_cursor.last_edge_id
    return response_cursor.last_change_seq


def run_once(config: Config, client: SyncClient, conn: sqlite3.Connection) -> int:
    cursors.ensure_local_tables(conn, config.sync_namespace)
    run_record.ensure_run_table(conn)
    db_epoch = cursors.get_or_create_db_epoch(conn)

    run_id = str(uuid.uuid4())
    started = _now_iso()
    run_record.start_run(conn, run_id, started)

    tables_synced = 0
    total_sent = 0
    total_rejected = 0
    had_failure = False
    error_detail: str | None = None
    sequence = 0

    for cfg in PRIORITY_ORDER:
        cursor_value = cursors.read_cursor(conn, config.sync_namespace, cfg.name, cfg.strategy)
        rows = readers.read_rows(conn, cfg, cursor_value)
        if not rows:
            continue
        sequence += 1
        envelope = _build_envelope(
            config, db_epoch, run_id, cfg, cursor_value, rows, sequence
        )
        try:
            response = client.post_batch(envelope)
        except BackpressureError as exc:
            had_failure = True
            error_detail = str(exc)
            break
        except RetriableError as exc:
            had_failure = True
            error_detail = str(exc)
            break
        except FatalBatchError as exc:
            had_failure = True
            error_detail = str(exc)
            break

        accepted_value = _accepted_value(response.accepted_cursor, cfg.strategy)
        if accepted_value is not None:
            cursors.advance_cursor(
                conn,
                config.sync_namespace,
                cfg.name,
                cfg.strategy,
                accepted_value,
                response.accepted,
                _now_iso(),
            )
        tables_synced += 1
        total_sent += response.accepted
        total_rejected += len(response.rejected)

    if had_failure:
        exit_code = EXIT_FAILED if tables_synced == 0 else EXIT_PARTIAL
        status = "failed" if tables_synced == 0 else "partial"
    elif total_rejected > 0:
        exit_code = EXIT_PARTIAL
        status = "partial"
    else:
        exit_code = EXIT_OK
        status = "ok"

    run_record.finish_run(
        conn,
        run_id,
        _now_iso(),
        status,
        tables_synced,
        total_sent,
        total_rejected,
        exit_code,
        error_detail,
    )
    return exit_code


def main() -> int:
    config = load_config()
    conn = sqlite3.connect(
        config.edge_db_path,
        timeout=config.edge_db_busy_timeout_s,
    )
    conn.execute(
        f"PRAGMA busy_timeout = {int(config.edge_db_busy_timeout_s * 1000)}"
    )
    client = SyncClient(config)
    try:
        return run_once(config, client, conn)
    finally:
        client.close()
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
