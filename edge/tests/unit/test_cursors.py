from __future__ import annotations

from petir_contracts import CursorStrategy

from sync_worker import cursors


def test_cursor_defaults_to_zero(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    assert cursors.read_cursor(empty_edge_conn, "system_events", CursorStrategy.append) == 0


def test_advance_and_read_append(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    cursors.advance_cursor(
        empty_edge_conn, "system_events", CursorStrategy.append, 5, 5, "2026-05-30T03:16:00Z"
    )
    assert cursors.read_cursor(empty_edge_conn, "system_events", CursorStrategy.append) == 5


def test_advance_and_read_summary(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    cursors.advance_cursor(
        empty_edge_conn,
        "weather_minute_summary",
        CursorStrategy.summary,
        42,
        3,
        "2026-05-30T03:16:00Z",
    )
    assert (
        cursors.read_cursor(empty_edge_conn, "weather_minute_summary", CursorStrategy.summary)
        == 42
    )


def test_rows_sent_accumulates(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    cursors.advance_cursor(empty_edge_conn, "system_events", CursorStrategy.append, 5, 5, "t")
    cursors.advance_cursor(empty_edge_conn, "system_events", CursorStrategy.append, 10, 5, "t")
    row = empty_edge_conn.execute(
        "SELECT rows_sent FROM sync_state WHERE table_name = 'system_events'"
    ).fetchone()
    assert row[0] == 10


def test_db_epoch_is_stable(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    first = cursors.get_or_create_db_epoch(empty_edge_conn)
    second = cursors.get_or_create_db_epoch(empty_edge_conn)
    assert first == second
    assert len(first) == 36
