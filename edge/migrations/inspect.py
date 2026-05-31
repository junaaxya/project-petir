from __future__ import annotations

import json
import sqlite3
import sys

DATA_TABLES = [
    "weather_samples",
    "weather_minute_summary",
    "lightning_events",
    "lightning_minute_summary",
    "weather_quality_events",
    "system_events",
]

SUMMARY_TABLES = ["weather_minute_summary", "lightning_minute_summary"]


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def columns(conn: sqlite3.Connection, table: str) -> list[str]:
    if not table_exists(conn, table):
        return []
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return column in columns(conn, table)


def list_triggers(conn: sqlite3.Connection) -> list[str]:
    return [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name"
        ).fetchall()
    ]


def row_count(conn: sqlite3.Connection, table: str) -> int:
    if not table_exists(conn, table):
        return 0
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def inspect(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        report: dict = {"db_path": db_path, "tables": {}, "triggers": list_triggers(conn)}
        for table in DATA_TABLES:
            report["tables"][table] = {
                "exists": table_exists(conn, table),
                "columns": columns(conn, table),
                "row_count": row_count(conn, table),
                "has_change_seq": has_column(conn, table, "change_seq"),
            }
        report["meta_exists"] = table_exists(conn, "meta")
        report["sync_state_exists"] = table_exists(conn, "sync_state")
        return report
    finally:
        conn.close()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m migrations.inspect <db_path>", file=sys.stderr)
        return 2
    print(json.dumps(inspect(argv[1]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
