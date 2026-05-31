from __future__ import annotations

import sqlite3

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.models.ops import SystemEvent
from sync_worker.client import SyncClient
from sync_worker.cursors import read_cursor
from sync_worker.run import run_once
from petir_contracts import CursorStrategy

from tests.e2e.conftest import make_config


def _count(engine, model) -> int:
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    s = maker()
    try:
        return s.execute(select(func.count()).select_from(model)).scalar_one()
    finally:
        s.close()


def test_disconnect_then_resume_stored_once(server, pg_engine, edge_db):
    config = make_config(server.base_url, edge_db)

    # First attempt while the server is DOWN -> nothing stored, edge cursor stays 0.
    server.stop()
    conn = sqlite3.connect(edge_db)
    client = SyncClient(config)
    try:
        first = run_once(config, client, conn)
    finally:
        client.close()
        conn.close()

    assert first == 2
    assert _count(pg_engine, SystemEvent) == 0
    conn = sqlite3.connect(edge_db)
    assert read_cursor(conn, "system_events", CursorStrategy.append) == 0
    conn.close()

    # Server back UP -> backlog drains, exactly once.
    server.start()
    conn = sqlite3.connect(edge_db)
    client = SyncClient(config)
    try:
        second = run_once(config, client, conn)
    finally:
        client.close()
        conn.close()

    assert second == 0
    assert _count(pg_engine, SystemEvent) == 5

    conn = sqlite3.connect(edge_db)
    assert read_cursor(conn, "system_events", CursorStrategy.append) == 5
    conn.close()

    # A further run with no new data must not duplicate.
    conn = sqlite3.connect(edge_db)
    client = SyncClient(config)
    try:
        third = run_once(config, client, conn)
    finally:
        client.close()
        conn.close()

    assert third == 0
    assert _count(pg_engine, SystemEvent) == 5
