from __future__ import annotations

import logging
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

from petir_contracts import CONTRACT_VERSION, CursorStrategy

from sync_worker import cursors, readers, run_record
from sync_worker.client import (
    AmbiguousBatchError,
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

logger = logging.getLogger(__name__)


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


def _failure_detail(
    outcome: str,
    table: str,
    local_cursor: int,
    server_cursor: int | None = None,
) -> str:
    detail = f"{outcome}; table={table}; local_cursor={local_cursor}"
    if server_cursor is not None:
        detail += f"; server_accepted_cursor={server_cursor}"
    return detail + "; cursor unchanged; verify server state before retry"


def _log_stop(
    outcome: str,
    table: str,
    local_cursor: int,
    server_cursor: int | None = None,
) -> None:
    logger.warning(
        "sync stopped outcome=%s table=%s local_cursor=%s "
        "server_accepted_cursor=%s cursor_unchanged=true "
        "guidance=verify_server_state_before_retry",
        outcome,
        table,
        local_cursor,
        server_cursor if server_cursor is not None else "unknown",
    )


def run_once(config: Config, client: SyncClient, conn: sqlite3.Connection) -> int:
    cursors.ensure_local_tables(conn)
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
        cursor_value = cursors.read_cursor(conn, cfg.name, cfg.strategy)
        rows = readers.read_rows(conn, cfg, cursor_value)
        if not rows:
            continue
        sequence += 1
        envelope = _build_envelope(
            config, db_epoch, run_id, cfg, cursor_value, rows, sequence
        )
        try:
            response = client.post_batch(envelope)
        except AmbiguousBatchError:
            had_failure = True
            error_detail = _failure_detail(
                "ambiguous request outcome", cfg.name, cursor_value
            )
            _log_stop("ambiguous", cfg.name, cursor_value)
            break
        except BackpressureError:
            had_failure = True
            error_detail = _failure_detail("server backpressure", cfg.name, cursor_value)
            _log_stop("backpressure", cfg.name, cursor_value)
            break
        except RetriableError:
            had_failure = True
            error_detail = _failure_detail("connection failure", cfg.name, cursor_value)
            _log_stop("connection_failure", cfg.name, cursor_value)
            break
        except FatalBatchError as exc:
            had_failure = True
            error_detail = _failure_detail(
                f"HTTP/ACK failure ({exc.status_code})",
                cfg.name,
                cursor_value,
                exc.accepted_cursor,
            )
            _log_stop(
                "http_or_ack_failure",
                cfg.name,
                cursor_value,
                exc.accepted_cursor,
            )
            break

        accepted_value = _accepted_value(response.accepted_cursor, cfg.strategy)
        if config.strict_first_sync and (
            response.status.value != "accepted" or response.rejected
        ):
            had_failure = True
            error_detail = _failure_detail(
                f"strict sync {response.status.value} ACK",
                cfg.name,
                cursor_value,
                accepted_value,
            )
            _log_stop(
                f"strict_{response.status.value}_ack",
                cfg.name,
                cursor_value,
                accepted_value,
            )
            break
        if config.strict_first_sync:
            logger.info(
                "strict sync ACK accepted table=%s local_cursor=%s "
                "server_accepted_cursor=%s rejected=0",
                cfg.name,
                cursor_value,
                accepted_value,
            )
        if accepted_value is not None:
            cursors.advance_cursor(
                conn,
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
    conn = sqlite3.connect(config.edge_db_path)
    client = SyncClient(config)
    try:
        return run_once(config, client, conn)
    finally:
        client.close()
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
