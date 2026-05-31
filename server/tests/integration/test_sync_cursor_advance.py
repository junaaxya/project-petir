from __future__ import annotations

from tests.conftest import NODE_ID, auth_headers, new_db_epoch, new_run_id


def _append_envelope(db_epoch: str, run_id: str, edge_ids: list[int]):
    return {
        "contract_version": "2.0.0",
        "node_id": NODE_ID,
        "db_epoch": db_epoch,
        "run_id": run_id,
        "table": "system_events",
        "cursor": {"strategy": "append", "last_edge_id": edge_ids[0] - 1},
        "rows": [
            {
                "edge_id": eid,
                "ts_pi_utc": "2026-05-30T03:15:42Z",
                "level": "info",
                "event_type": "boot",
                "message": f"event {eid}",
                "created_at_utc": "2026-05-30T03:15:42Z",
            }
            for eid in edge_ids
        ],
    }


def test_append_cursor_advances(client):
    db_epoch = new_db_epoch()
    r1 = client.post(
        "/api/ingest/sync-batch",
        json=_append_envelope(db_epoch, new_run_id(), [1, 2, 3, 4, 5]),
        headers=auth_headers(),
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["accepted_cursor"]["last_edge_id"] == 5

    r2 = client.post(
        "/api/ingest/sync-batch",
        json=_append_envelope(db_epoch, new_run_id(), [6, 7, 8, 9, 10]),
        headers=auth_headers(),
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["accepted_cursor"]["last_edge_id"] == 10


def test_db_epoch_change_resets_cursor(client, session):
    from app.models.registry import SyncCursor

    db_epoch_a = new_db_epoch()
    client.post(
        "/api/ingest/sync-batch",
        json=_append_envelope(db_epoch_a, new_run_id(), [1, 2, 3]),
        headers=auth_headers(),
    )
    cur = session.get(SyncCursor, {"node_id": NODE_ID, "table_name": "system_events"})
    session.refresh(cur)
    assert cur.last_edge_id == 3

    db_epoch_b = new_db_epoch()
    r = client.post(
        "/api/ingest/sync-batch",
        json=_append_envelope(db_epoch_b, new_run_id(), [1, 2]),
        headers=auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["accepted_cursor"]["last_edge_id"] == 2
    session.expire_all()
    cur2 = session.get(SyncCursor, {"node_id": NODE_ID, "table_name": "system_events"})
    assert str(cur2.db_epoch) == db_epoch_b
