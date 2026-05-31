from __future__ import annotations

import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from migrations.inspect import SUMMARY_TABLES, has_column, table_exists

_MIGRATIONS_DIR = Path(__file__).resolve().parent


def backup_db(db_path: str) -> str:
    src = Path(db_path)
    if not src.exists():
        raise FileNotFoundError(f"edge DB not found: {db_path}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = src.with_name(f"{src.name}.backup-{stamp}")
    shutil.copy2(src, dest)
    if not dest.exists() or dest.stat().st_size == 0:
        raise RuntimeError(f"backup failed or empty: {dest}")
    return str(dest)


def _exec_script(conn: sqlite3.Connection, filename: str) -> None:
    sql = (_MIGRATIONS_DIR / filename).read_text()
    conn.executescript(sql)
    conn.commit()


def _ensure_identity(conn: sqlite3.Connection) -> None:
    for key, factory in (("pi_id", lambda: f"pi-{uuid.uuid4().hex[:12]}"),
                         ("db_epoch", lambda: str(uuid.uuid4()))):
        row = conn.execute("SELECT 1 FROM meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO meta(key, value) VALUES(?, ?)", (key, factory()))
    conn.commit()


def _backfill_change_seq(conn: sqlite3.Connection, table: str) -> int:
    # Backfill runs BEFORE the change_seq triggers exist, so these UPDATEs do not
    # recursively fire the counter; existing rows get deterministic monotonic seqs
    # ordered by their natural key, and the counter is set to the max so the live
    # triggers continue from there.
    rows = conn.execute(
        f"SELECT rowid FROM {table} WHERE change_seq IS NULL "
        f"ORDER BY minute_utc ASC, source ASC, device ASC"
    ).fetchall()
    if not rows:
        return 0
    start = conn.execute(
        "SELECT value FROM change_seq_counter WHERE table_name = ?", (table,)
    ).fetchone()
    seq = start[0] if start else 0
    for (rowid,) in rows:
        seq += 1
        conn.execute(
            f"UPDATE {table} SET change_seq = ? WHERE rowid = ?", (seq, rowid)
        )
    conn.execute(
        "INSERT INTO change_seq_counter(table_name, value) VALUES(?, ?) "
        "ON CONFLICT(table_name) DO UPDATE SET value = excluded.value",
        (table, seq),
    )
    conn.commit()
    return len(rows)


def apply_migration(db_path: str, *, do_backup: bool = True) -> dict:
    result: dict = {"backup": None, "backfilled": {}, "added_column": []}
    if do_backup:
        result["backup"] = backup_db(db_path)

    conn = sqlite3.connect(db_path)
    try:
        _exec_script(conn, "0001_meta_sync_state.sql")

        conn.execute(
            "CREATE TABLE IF NOT EXISTS change_seq_counter ("
            "table_name TEXT PRIMARY KEY, value INTEGER NOT NULL DEFAULT 0)"
        )
        conn.commit()

        for table in SUMMARY_TABLES:
            if not table_exists(conn, table):
                continue
            if not has_column(conn, table, "change_seq"):
                conn.execute(f"ALTER TABLE {table} ADD COLUMN change_seq INTEGER")
                conn.commit()
                result["added_column"].append(table)
            result["backfilled"][table] = _backfill_change_seq(conn, table)

        _exec_script(conn, "0002_summary_change_seq.sql")
        _ensure_identity(conn)
        return result
    finally:
        conn.close()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m migrations.apply <db_path> [--no-backup]", file=sys.stderr)
        return 2
    do_backup = "--no-backup" not in argv[2:]
    result = apply_migration(argv[1], do_backup=do_backup)
    print(f"backup: {result['backup']}")
    print(f"added_column: {result['added_column']}")
    print(f"backfilled: {result['backfilled']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
