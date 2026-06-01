from __future__ import annotations

import sqlite3
import uuid

from petir_contracts import CursorStrategy

_SYNC_STATE_NAMESPACE_TABLE = "sync_state_v2"
_SYNC_STATE_DDL = f"""
CREATE TABLE IF NOT EXISTS {_SYNC_STATE_NAMESPACE_TABLE} (
    sync_namespace  TEXT NOT NULL,
    table_name      TEXT NOT NULL,
    last_edge_id    INTEGER,
    last_change_seq INTEGER,
    last_acked_at   TEXT,
    rows_sent       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (sync_namespace, table_name)
)
"""

_META_DDL = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _seed_namespaced_state_from_legacy(
    conn: sqlite3.Connection,
    sync_namespace: str,
) -> None:
    seeded_key = "sync_state_namespaced_seeded"
    if get_meta(conn, seeded_key) == "1":
        return
    if not _table_exists(conn, "sync_state"):
        set_meta(conn, seeded_key, "1")
        return
    has_rows = conn.execute(
        f"SELECT 1 FROM {_SYNC_STATE_NAMESPACE_TABLE} WHERE sync_namespace = ? LIMIT 1",
        (sync_namespace,),
    ).fetchone()
    if has_rows is not None:
        set_meta(conn, seeded_key, "1")
        return

    legacy_rows = conn.execute(
        "SELECT table_name, last_edge_id, last_change_seq, last_acked_at, rows_sent FROM sync_state"
    ).fetchall()
    if legacy_rows:
        conn.executemany(
            f"INSERT INTO {_SYNC_STATE_NAMESPACE_TABLE}("
            "sync_namespace, table_name, last_edge_id, last_change_seq, last_acked_at, rows_sent"
            ") VALUES(?, ?, ?, ?, ?, ?)",
            [
                (
                    sync_namespace,
                    table_name,
                    last_edge_id,
                    last_change_seq,
                    last_acked_at,
                    rows_sent,
                )
                for table_name, last_edge_id, last_change_seq, last_acked_at, rows_sent in legacy_rows
            ],
        )
        conn.commit()
    set_meta(conn, seeded_key, "1")


def ensure_local_tables(conn: sqlite3.Connection, sync_namespace: str | None = None) -> None:
    conn.execute(_SYNC_STATE_DDL)
    conn.execute(_META_DDL)
    conn.commit()
    if sync_namespace is not None:
        _seed_namespaced_state_from_legacy(conn, sync_namespace)


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


def read_cursor(
    conn: sqlite3.Connection,
    sync_namespace: str,
    table: str,
    strategy: CursorStrategy,
) -> int:
    row = conn.execute(
        f"SELECT last_edge_id, last_change_seq FROM {_SYNC_STATE_NAMESPACE_TABLE} "
        "WHERE sync_namespace = ? AND table_name = ?",
        (sync_namespace, table),
    ).fetchone()
    if row is None:
        return 0
    value = row[0] if strategy is CursorStrategy.append else row[1]
    return value if value is not None else 0


def advance_cursor(
    conn: sqlite3.Connection,
    sync_namespace: str,
    table: str,
    strategy: CursorStrategy,
    value: int,
    rows_added: int,
    acked_at: str,
) -> None:
    column = "last_edge_id" if strategy is CursorStrategy.append else "last_change_seq"
    conn.execute(
        f"INSERT INTO {_SYNC_STATE_NAMESPACE_TABLE}(sync_namespace, table_name, {column}, last_acked_at, rows_sent) "
        f"VALUES(?, ?, ?, ?, ?) "
        f"ON CONFLICT(sync_namespace, table_name) DO UPDATE SET "
        f"{column} = excluded.{column}, "
        f"last_acked_at = excluded.last_acked_at, "
        f"rows_sent = {_SYNC_STATE_NAMESPACE_TABLE}.rows_sent + excluded.rows_sent",
        (sync_namespace, table, value, acked_at, rows_added),
    )
    conn.commit()
