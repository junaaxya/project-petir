from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest

from petir_contracts import CursorStrategy

from sync_worker import cursors
from sync_worker.client import SyncClient
from sync_worker.config import Config
from sync_worker.run import EXIT_FAILED, EXIT_OK, run_once

_BASE_CONFIG = Config(
    server_url="http://mock.local",
    node_id="rpi-test-01",
    node_token="top-secret-node-token",
    edge_db_path=":memory:",
    request_timeout_s=1.0,
    max_retries=0,
    backoff_base_s=0.0,
    backoff_cap_s=0.0,
)
_STRICT_CONFIG = replace(_BASE_CONFIG, strict_first_sync=True)


def _client(config: Config, handler) -> SyncClient:
    return SyncClient(
        config,
        httpx.Client(transport=httpx.MockTransport(handler), timeout=1.0),
    )


def _response(
    request: httpx.Request,
    *,
    status: str = "accepted",
    accepted: int | None = None,
    rejected: list[dict] | None = None,
    accepted_cursor: int | None = None,
) -> httpx.Response:
    body = json.loads(request.content)
    rows = body["rows"]
    strategy = body["cursor"]["strategy"]
    row_key = "edge_id" if strategy == "append" else "change_seq"
    cursor_key = "last_edge_id" if strategy == "append" else "last_change_seq"
    return httpx.Response(
        200,
        json={
            "run_id": body["run_id"],
            "table": body["table"],
            "status": status,
            "accepted": len(rows) if accepted is None else accepted,
            "rejected": [] if rejected is None else rejected,
            "accepted_cursor": {
                "strategy": strategy,
                cursor_key: max(row[row_key] for row in rows)
                if accepted_cursor is None
                else accepted_cursor,
            },
            "server_contract_version": "2.1.0",
        },
        request=request,
    )


def _run_result(conn) -> tuple[str, str | None]:
    row = conn.execute(
        "SELECT status, error_detail FROM sync_runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    return row


def test_strict_mode_accepts_full_ack_and_advances(edge_conn, caplog):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content)["table"])
        return _response(request)

    with caplog.at_level("INFO"):
        exit_code = run_once(
            _STRICT_CONFIG, _client(_STRICT_CONFIG, handler), edge_conn
        )

    assert exit_code == EXIT_OK
    assert seen[:2] == ["system_events", "weather_minute_summary"]
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 5
    assert "local_cursor=0 server_accepted_cursor=5" in caplog.text
    assert "top-secret-node-token" not in caplog.text


@pytest.mark.parametrize(
    ("status", "accepted", "rejected"),
    [
        ("accepted", 4, [{"index": 4, "reason": "invalid sensor secret-value"}]),
        ("partial", 4, [{"index": 4, "reason": "invalid sensor secret-value"}]),
        (
            "rejected",
            0,
            [{"index": index, "reason": "invalid"} for index in range(5)],
        ),
    ],
)
def test_strict_mode_stops_on_non_full_ack_without_advancing_or_next_table(
    edge_conn, caplog, status, accepted, rejected
):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content)["table"])
        return _response(
            request, status=status, accepted=accepted, rejected=rejected
        )

    with caplog.at_level("WARNING"):
        exit_code = run_once(_STRICT_CONFIG, _client(_STRICT_CONFIG, handler), edge_conn)

    assert exit_code == EXIT_FAILED
    assert seen == ["system_events"]
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 0
    run_status, detail = _run_result(edge_conn)
    assert run_status == "failed"
    assert "local_cursor=0" in (detail or "")
    assert "server_accepted_cursor=5" in (detail or "")
    assert "cursor unchanged" in (detail or "")
    assert "local_cursor=0" in caplog.text
    assert "server_accepted_cursor=5" in caplog.text
    assert "top-secret-node-token" not in caplog.text
    assert "secret-value" not in caplog.text


def test_default_non_strict_mode_keeps_partial_ack_compatibility(edge_conn):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body["table"])
        if body["table"] == "system_events":
            return _response(
                request,
                status="partial",
                accepted=4,
                rejected=[{"index": 4, "reason": "invalid"}],
            )
        return _response(request)

    exit_code = run_once(_BASE_CONFIG, _client(_BASE_CONFIG, handler), edge_conn)

    assert exit_code == 1
    assert seen[:2] == ["system_events", "weather_minute_summary"]
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 5


def test_strict_mode_rejects_lower_ack_cursor_and_logs_safe_cursor_state(
    edge_conn, caplog
):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content)["table"])
        return _response(request, accepted_cursor=4)

    with caplog.at_level("WARNING"):
        exit_code = run_once(_STRICT_CONFIG, _client(_STRICT_CONFIG, handler), edge_conn)

    assert exit_code == EXIT_FAILED
    assert seen == ["system_events"]
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 0
    assert "local_cursor=0" in caplog.text
    assert "server_accepted_cursor=4" in caplog.text
    assert "top-secret-node-token" not in caplog.text


def test_strict_timeout_is_ambiguous_and_is_not_replayed(edge_conn, caplog):
    attempts = 0
    config = replace(_STRICT_CONFIG, max_retries=3)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("token=leaked-timeout-secret", request=request)

    with caplog.at_level("WARNING"):
        exit_code = run_once(config, _client(config, handler), edge_conn)

    assert exit_code == EXIT_FAILED
    assert attempts == 1
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 0
    _, detail = _run_result(edge_conn)
    assert "ambiguous" in (detail or "")
    assert "verify server state before retry" in (detail or "")
    assert "leaked-timeout-secret" not in (detail or "")
    assert "ambiguous" in caplog.text
    assert "leaked-timeout-secret" not in caplog.text


def test_default_mode_retries_timeout_and_accepts_later_ack(edge_conn):
    attempts = 0
    config = replace(_BASE_CONFIG, max_retries=1)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("uncertain", request=request)
        return _response(request)

    exit_code = run_once(config, _client(config, handler), edge_conn)

    assert exit_code == EXIT_OK
    assert attempts >= 2
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 5


def test_strict_connection_error_stops_without_advancing_or_next_table(edge_conn):
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("offline", request=request)

    exit_code = run_once(
        _STRICT_CONFIG, _client(_STRICT_CONFIG, handler), edge_conn
    )

    assert exit_code == EXIT_FAILED
    assert attempts == 1
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 0


@pytest.mark.parametrize("status_code", [400, 401, 429, 500, 503])
def test_strict_http_failure_stops_without_advancing(edge_conn, status_code):
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            status_code, text="token=server-secret", request=request
        )

    exit_code = run_once(
        _STRICT_CONFIG, _client(_STRICT_CONFIG, handler), edge_conn
    )

    assert exit_code == EXIT_FAILED
    assert attempts == 1
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 0
    _, detail = _run_result(edge_conn)
    assert "server-secret" not in (detail or "")


def test_max_retries_counts_retries_after_initial_attempt(edge_conn):
    attempts = 0
    config = replace(_STRICT_CONFIG, max_retries=2)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, request=request)

    exit_code = run_once(config, _client(config, handler), edge_conn)

    assert exit_code == EXIT_FAILED
    assert attempts == 3
    assert cursors.read_cursor(edge_conn, "system_events", CursorStrategy.append) == 0
