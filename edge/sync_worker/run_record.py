from __future__ import annotations

import sqlite3

_SYNC_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS sync_runs (
    run_id        TEXT PRIMARY KEY,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    status        TEXT,
    tables_count  INTEGER DEFAULT 0,
    rows_sent     INTEGER DEFAULT 0,
    rows_rejected INTEGER DEFAULT 0,
    exit_code     INTEGER,
    error_detail  TEXT
)
"""


def ensure_run_table(conn: sqlite3.Connection) -> None:
    conn.execute(_SYNC_RUNS_DDL)
    conn.commit()


def start_run(conn: sqlite3.Connection, run_id: str, started_at: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sync_runs(run_id, started_at, status) VALUES(?, ?, ?)",
        (run_id, started_at, "running"),
    )
    conn.commit()


def finish_run(
    conn: sqlite3.Connection,
    run_id: str,
    finished_at: str,
    status: str,
    tables_count: int,
    rows_sent: int,
    rows_rejected: int,
    exit_code: int,
    error_detail: str | None,
) -> None:
    conn.execute(
        "UPDATE sync_runs SET finished_at = ?, status = ?, tables_count = ?, "
        "rows_sent = ?, rows_rejected = ?, exit_code = ?, error_detail = ? "
        "WHERE run_id = ?",
        (
            finished_at,
            status,
            tables_count,
            rows_sent,
            rows_rejected,
            exit_code,
            error_detail,
            run_id,
        ),
    )
    conn.commit()
