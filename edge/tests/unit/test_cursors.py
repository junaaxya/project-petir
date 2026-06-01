from __future__ import annotations

from petir_contracts import CursorStrategy

from sync_worker import cursors


_NAMESPACE = "node-a|https://server-a.example"


def test_cursor_defaults_to_zero(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    assert cursors.read_cursor(empty_edge_conn, _NAMESPACE, "system_events", CursorStrategy.append) == 0


def test_advance_and_read_append(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    cursors.advance_cursor(
        empty_edge_conn,
        _NAMESPACE,
        "system_events",
        CursorStrategy.append,
        5,
        5,
        "2026-05-30T03:16:00Z"
    )
    assert cursors.read_cursor(empty_edge_conn, _NAMESPACE, "system_events", CursorStrategy.append) == 5


def test_advance_and_read_summary(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    cursors.advance_cursor(
        empty_edge_conn,
        _NAMESPACE,
        "weather_minute_summary",
        CursorStrategy.summary,
        42,
        3,
        "2026-05-30T03:16:00Z",
    )
    assert (
        cursors.read_cursor(empty_edge_conn, _NAMESPACE, "weather_minute_summary", CursorStrategy.summary)
        == 42
    )


def test_rows_sent_accumulates(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    cursors.advance_cursor(empty_edge_conn, _NAMESPACE, "system_events", CursorStrategy.append, 5, 5, "t")
    cursors.advance_cursor(empty_edge_conn, _NAMESPACE, "system_events", CursorStrategy.append, 10, 5, "t")
    row = empty_edge_conn.execute(
        "SELECT rows_sent FROM sync_state_v2 WHERE sync_namespace = ? AND table_name = 'system_events'",
        (_NAMESPACE,),
    ).fetchone()
    assert row[0] == 10


def test_db_epoch_is_stable(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    first = cursors.get_or_create_db_epoch(empty_edge_conn)
    second = cursors.get_or_create_db_epoch(empty_edge_conn)
    assert first == second
    assert len(first) == 36


def test_cursors_are_namespaced_by_sync_identity(empty_edge_conn):
    cursors.ensure_local_tables(empty_edge_conn)
    ns_a = "node-a|https://server-a.example"
    ns_b = "node-b|https://server-b.example"

    cursors.advance_cursor(
        empty_edge_conn,
        ns_a,
        "system_events",
        CursorStrategy.append,
        5,
        5,
        "2026-05-30T03:16:00Z",
    )

    assert cursors.read_cursor(empty_edge_conn, ns_a, "system_events", CursorStrategy.append) == 5
    assert cursors.read_cursor(empty_edge_conn, ns_b, "system_events", CursorStrategy.append) == 0
