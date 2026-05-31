from __future__ import annotations

import json
import sqlite3
from typing import Any

from petir_contracts import CursorStrategy

from sync_worker.normalize import normalize_row
from sync_worker.tables import TableConfig


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def _row_to_dict(
    raw: sqlite3.Row, columns: list[str], cfg: TableConfig, has_change_seq: bool
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in columns:
        out[col] = raw[col]
    if cfg.strategy is CursorStrategy.append:
        out["edge_id"] = raw["id"]
        out.pop("id", None)
    else:
        out["change_seq"] = raw["change_seq"]
    rj = out.get("raw_json")
    if isinstance(rj, str):
        try:
            out["raw_json"] = json.loads(rj)
        except (ValueError, TypeError):
            pass
    return out


def read_rows(
    conn: sqlite3.Connection, cfg: TableConfig, cursor_value: int
) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    cols = _table_columns(conn, cfg.source_table)
    if cfg.strategy is CursorStrategy.append:
        order_col = "id"
        select_cols = sorted(cols)
    else:
        order_col = "change_seq"
        select_cols = sorted(cols)
    col_sql = ", ".join(f'"{c}"' for c in select_cols)
    sql = (
        f"SELECT {col_sql} FROM {cfg.source_table} "
        f"WHERE {order_col} > ? ORDER BY {order_col} ASC LIMIT ?"
    )
    raw_rows = conn.execute(sql, (cursor_value, cfg.limit)).fetchall()
    has_cs = "change_seq" in cols
    return [normalize_row(cfg.name, _row_to_dict(r, select_cols, cfg, has_cs)) for r in raw_rows]


def max_cursor(rows: list[dict[str, Any]], cfg: TableConfig) -> int | None:
    field = cfg.cursor_field
    seen = [r[field] for r in rows if isinstance(r.get(field), int)]
    return max(seen) if seen else None
