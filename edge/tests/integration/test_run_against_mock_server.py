from __future__ import annotations

import httpx
import pytest

from petir_contracts import CursorStrategy

from sync_worker import cursors
from sync_worker.client import SyncClient
from sync_worker.config import Config
from sync_worker.run import run_once

_CONFIG = Config(
    server_url="http://mock.local",
    node_id="rpi-test-01",
    node_token="tok",
    edge_db_path=":memory:",
    request_timeout_s=1.0,
    max_retries=2,
    backoff_base_s=0.0,
    backoff_cap_s=0.0,
)


def _make_client(handler) -> SyncClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, timeout=1.0)
    return SyncClient(_CONFIG, client=http)


def _ack(request: httpx.Request) -> httpx.Response:
    import json

    body = json.loads(request.content)
    table = body["table"]
    rows = body["rows"]
    strategy = body["cursor"].get("strategy")
    if strategy == "append":
        max_key = max(r["edge_id"] for r in rows)
        accepted_cursor = {"strategy": "append", "last_edge_id": max_key}
    else:
        max_key = max(r["change_seq"] for r in rows)
        accepted_cursor = {"strategy": "summary", "last_change_seq": max_key}
    return httpx.Response(
        200,
        json={
            "run_id": body["run_id"],
            "table": table,
            "status": "accepted",
            "accepted": len(rows),
            "rejected": [],
            "accepted_cursor": accepted_cursor,
            "server_contract_version": "1.0.0",
        },
    )


def test_full_run_acks_and_advances_cursors(edge_conn):
    seen_tables: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen_tables.append(json.loads(request.content)["table"])
        return _ack(request)

    client = _make_client(handler)
    exit_code = run_once(_CONFIG, client, edge_conn)

    assert exit_code == 0
    assert seen_tables[0] == "system_events"
    assert "weather_minute_summary" in seen_tables
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 5
    assert (
        cursors.read_cursor(edge_conn, "weather_minute_summary", CursorStrategy.summary) == 3
    )


def test_no_data_run_is_ok(empty_edge_conn):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not POST when there is no data")

    client = _make_client(handler)
    exit_code = run_once(_CONFIG, client, empty_edge_conn)
    assert exit_code == 0


def test_server_5xx_does_not_advance_cursor(edge_conn):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    client = _make_client(handler)
    exit_code = run_once(_CONFIG, client, edge_conn)

    assert exit_code == 2
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 0


def test_resume_after_transient_failure(edge_conn):
    state = {"runs_failed": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if state["runs_failed"] < 1:
            return httpx.Response(503, text="temporary")
        return _ack(request)

    client = _make_client(handler)
    first = run_once(_CONFIG, client, edge_conn)
    assert first == 2
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 0

    state["runs_failed"] = 1
    second = run_once(_CONFIG, client, edge_conn)
    assert second == 0
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 5


def test_transient_5xx_retried_within_single_run(edge_conn):
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        if json.loads(request.content)["table"] == "system_events":
            attempts["n"] += 1
            if attempts["n"] == 1:
                return httpx.Response(503, text="blip")
        return _ack(request)

    client = _make_client(handler)
    exit_code = run_once(_CONFIG, client, edge_conn)
    assert exit_code == 0
    assert attempts["n"] >= 2
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 5
