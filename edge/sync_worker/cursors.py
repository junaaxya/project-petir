from __future__ import annotations

import sqlite3
import uuid

from petir_contracts import CursorStrategy

_SYNC_STATE_DDL = """
CREATE TABLE IF NOT EXISTS sync_state (
    table_name      TEXT PRIMARY KEY,
    last_edge_id    INTEGER,
    last_change_seq INTEGER,
    last_acked_at   TEXT,
    rows_sent       INTEGER NOT NULL DEFAULT 0
)
"""

_META_DDL = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""


def ensure_local_tables(conn: sqlite3.Connection) -> None:
    conn.execute(_SYNC_STATE_DDL)
    conn.execute(_META_DDL)
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def get_or_create_db_epoch(conn: sqlite3.Connection) -> str:
    epoch = get_meta(conn, "db_epoch")
    if epoch is None:
        epoch = str(uuid.uuid4())
        set_meta(conn, "db_epoch", epoch)
    return epoch


def read_cursor(conn: sqlite3.Connection, table: str, strategy: CursorStrategy) -> int:
    row = conn.execute(
        "SELECT last_edge_id, last_change_seq FROM sync_state WHERE table_name = ?",
        (table,),
    ).fetchone()
    if row is None:
        return 0
    value = row[0] if strategy is CursorStrategy.append else row[1]
    return value if value is not None else 0


def advance_cursor(
    conn: sqlite3.Connection,
    table: str,
    strategy: CursorStrategy,
    value: int,
    rows_added: int,
    acked_at: str,
) -> None:
    column = "last_edge_id" if strategy is CursorStrategy.append else "last_change_seq"
    conn.execute(
        f"INSERT INTO sync_state(table_name, {column}, last_acked_at, rows_sent) "
        f"VALUES(?, ?, ?, ?) "
        f"ON CONFLICT(table_name) DO UPDATE SET "
        f"{column} = excluded.{column}, "
        f"last_acked_at = excluded.last_acked_at, "
        f"rows_sent = sync_state.rows_sent + excluded.rows_sent",
        (table, value, acked_at, rows_added),
    )
    conn.commit()
