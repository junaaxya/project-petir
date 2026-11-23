from __future__ import annotations

from copy import deepcopy

import httpx
import pytest

from sync_worker.client import FatalBatchError, SyncClient
from sync_worker.config import Config

RUN_ID = "11111111-1111-4111-8111-111111111111"


def _config() -> Config:
    return Config(
        server_url="https://petir2.invalid",
        node_id="rpi-test-01",
        node_token="test-token",
        edge_db_path=":memory:",
        request_timeout_s=1,
        max_retries=0,
        backoff_base_s=0,
        backoff_cap_s=0,
    )


def _envelope() -> dict:
    return {
        "contract_version": "2.1.0",
        "node_id": "rpi-test-01",
        "db_epoch": "22222222-2222-4222-8222-222222222222",
        "run_id": RUN_ID,
        "table": "system_events",
        "cursor": {"strategy": "append", "last_edge_id": 10},
        "rows": [{"edge_id": 11, "created_at_utc": "2026-01-01T00:00:00Z"}],
        "sequence": 1,
        "started_at_utc": "2026-01-01T00:00:00Z",
    }


def _ack() -> dict:
    return {
        "server_contract_version": "2.1.0",
        "run_id": RUN_ID,
        "table": "system_events",
        "status": "accepted",
        "accepted": 1,
        "rejected": [],
        "accepted_cursor": {"strategy": "append", "last_edge_id": 11},
    }


def _client_for(payload: dict) -> SyncClient:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=payload, request=request)
    )
    return SyncClient(_config(), httpx.Client(transport=transport))


def test_post_batch_accepts_matching_ack():
    client = _client_for(_ack())
    try:
        response = client.post_batch(_envelope())
    finally:
        client.close()
    assert response.accepted == 1
    assert response.accepted_cursor.last_edge_id == 11


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("run_id",), "33333333-3333-4333-8333-333333333333"),
        (("table",), "lightning_events"),
        (("server_contract_version",), "3.0.0"),
        (("accepted_cursor", "strategy"), "summary"),
        (("accepted_cursor", "last_edge_id"), 9),
        (("accepted_cursor", "last_edge_id"), 12),
        (("accepted_cursor", "last_edge_id"), None),
        (("accepted",), 2),
        (("accepted",), 0),
    ],
)
def test_post_batch_rejects_mismatched_ack(path, value):
    payload = deepcopy(_ack())
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    client = _client_for(payload)
    try:
        with pytest.raises(FatalBatchError, match="invalid ACK"):
            client.post_batch(_envelope())
    finally:
        client.close()


def test_post_batch_rejects_out_of_range_rejection_index():
    payload = _ack()
    payload["accepted"] = 0
    payload["rejected"] = [{"index": 1, "reason": "bad"}]

    client = _client_for(payload)
    try:
        with pytest.raises(FatalBatchError, match="outside batch"):
            client.post_batch(_envelope())
    finally:
        client.close()


def test_post_batch_rejects_summary_cursor_outside_batch():
    envelope = _envelope()
    envelope["table"] = "weather_minute_summary"
    envelope["cursor"] = {"strategy": "summary", "last_change_seq": 20}
    envelope["rows"] = [
        {"change_seq": 21, "minute_utc": "2026-01-01T00:00:00Z"}
    ]

    payload = _ack()
    payload["table"] = "weather_minute_summary"
    payload["accepted_cursor"] = {
        "strategy": "summary",
        "last_change_seq": 22,
    }

    client = _client_for(payload)
    try:
        with pytest.raises(FatalBatchError, match="cursor does not match batch"):
            client.post_batch(envelope)
    finally:
        client.close()
