from __future__ import annotations

import sqlite3

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.models.registry import SyncCursor
from app.models.ops import SystemEvent
from app.models.weather import WeatherMinuteSummary
from sync_worker.client import SyncClient
from sync_worker.run import run_once

from tests.e2e.conftest import NODE_ID, make_config


def _count(engine, model) -> int:
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    s = maker()
    try:
        return s.execute(select(func.count()).select_from(model)).scalar_one()
    finally:
        s.close()


def _server_cursor(engine, table: str):
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    s = maker()
    try:
        return s.get(SyncCursor, {"node_id": NODE_ID, "table_name": table})
    finally:
        s.close()


def test_full_pi_to_pg_flow(server, pg_engine, edge_db):
    config = make_config(server.base_url, edge_db)
    conn = sqlite3.connect(edge_db)
    client = SyncClient(config)
    try:
        exit_code = run_once(config, client, conn)
    finally:
        client.close()
        conn.close()

    assert exit_code == 0
    assert _count(pg_engine, SystemEvent) == 5
    assert _count(pg_engine, WeatherMinuteSummary) == 3

    sys_cursor = _server_cursor(pg_engine, "system_events")
    assert sys_cursor is not None
    assert sys_cursor.last_edge_id == 5

    wms_cursor = _server_cursor(pg_engine, "weather_minute_summary")
    assert wms_cursor is not None
    assert wms_cursor.last_change_seq == 3


def test_rerun_is_stored_once(server, pg_engine, edge_db):
    config = make_config(server.base_url, edge_db)

    for _ in range(2):
        conn = sqlite3.connect(edge_db)
        client = SyncClient(config)
        try:
            run_once(config, client, conn)
        finally:
            client.close()
            conn.close()

    assert _count(pg_engine, SystemEvent) == 5
    assert _count(pg_engine, WeatherMinuteSummary) == 3
