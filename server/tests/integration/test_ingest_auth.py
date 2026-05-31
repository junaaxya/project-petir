from __future__ import annotations

from tests.conftest import NODE_ID, auth_headers, new_db_epoch, new_run_id


def _min_envelope(table: str, rows: list[dict], db_epoch: str, run_id: str):
    return {
        "contract_version": "2.0.0",
        "node_id": NODE_ID,
        "db_epoch": db_epoch,
        "run_id": run_id,
        "table": table,
        "cursor": {"strategy": "append", "last_edge_id": 0},
        "rows": rows,
    }


def _row():
    return [
        {
            "edge_id": 1,
            "ts_pi_utc": "2026-05-30T03:15:42Z",
            "level": "info",
            "created_at_utc": "2026-05-30T03:15:42Z",
        }
    ]


def test_missing_token_401(client):
    r = client.post(
        "/api/ingest/sync-batch",
        json=_min_envelope("system_events", _row(), new_db_epoch(), new_run_id()),
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "BAD_TOKEN"


def test_wrong_token_401(client):
    r = client.post(
        "/api/ingest/sync-batch",
        json=_min_envelope("system_events", _row(), new_db_epoch(), new_run_id()),
        headers=auth_headers("wrong-token"),
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "BAD_TOKEN"


def test_node_mismatch_409(client):
    env = _min_envelope("system_events", _row(), new_db_epoch(), new_run_id())
    env["node_id"] = "some-other-node"
    r = client.post("/api/ingest/sync-batch", json=env, headers=auth_headers())
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "NODE_MISMATCH"


def test_bad_contract_major_426(client):
    env = _min_envelope("system_events", _row(), new_db_epoch(), new_run_id())
    env["contract_version"] = "1.0.0"
    r = client.post("/api/ingest/sync-batch", json=env, headers=auth_headers())
    assert r.status_code == 426
    assert r.json()["error"]["code"] == "CONTRACT_INCOMPATIBLE"


def test_invalid_envelope_422(client):
    r = client.post(
        "/api/ingest/sync-batch",
        json={"node_id": NODE_ID, "rows": []},
        headers=auth_headers(),
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_ENVELOPE"


def test_disabled_node_403(client, session):
    from app.models.registry import EdgeNode

    node = session.get(EdgeNode, NODE_ID)
    node.enabled = False
    session.commit()
    r = client.post(
        "/api/ingest/sync-batch",
        json=_min_envelope("system_events", _row(), new_db_epoch(), new_run_id()),
        headers=auth_headers(),
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "NODE_DISABLED"
