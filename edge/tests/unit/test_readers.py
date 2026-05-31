from __future__ import annotations

from sync_worker import readers
from sync_worker.tables import BY_NAME


def test_append_reader_returns_edge_id_not_id(edge_conn):
    cfg = BY_NAME["system_events"]
    rows = readers.read_rows(edge_conn, cfg, 0)
    assert len(rows) == 5
    assert "edge_id" in rows[0]
    assert "id" not in rows[0]
    assert [r["edge_id"] for r in rows] == [1, 2, 3, 4, 5]


def test_append_reader_respects_cursor(edge_conn):
    cfg = BY_NAME["system_events"]
    rows = readers.read_rows(edge_conn, cfg, 3)
    assert [r["edge_id"] for r in rows] == [4, 5]


def test_summary_reader_uses_change_seq(edge_conn):
    cfg = BY_NAME["weather_minute_summary"]
    rows = readers.read_rows(edge_conn, cfg, 0)
    assert len(rows) == 3
    assert [r["change_seq"] for r in rows] == [1, 2, 3]


def test_summary_reader_respects_cursor(edge_conn):
    cfg = BY_NAME["weather_minute_summary"]
    rows = readers.read_rows(edge_conn, cfg, 2)
    assert [r["change_seq"] for r in rows] == [3]


def test_limit_applies(edge_conn):
    cfg = BY_NAME["system_events"]
    limited = readers.read_rows(edge_conn, type(cfg)(cfg.name, cfg.strategy, cfg.cursor_field, cfg.source_table, 2), 0)
    assert len(limited) == 2


def test_max_cursor(edge_conn):
    cfg = BY_NAME["system_events"]
    rows = readers.read_rows(edge_conn, cfg, 0)
    assert readers.max_cursor(rows, cfg) == 5
