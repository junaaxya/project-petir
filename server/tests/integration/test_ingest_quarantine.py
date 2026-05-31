from __future__ import annotations

from tests.conftest import NODE_ID, auth_headers, new_db_epoch, new_run_id


def _envelope_with_poison(db_epoch: str, run_id: str):
    return {
        "contract_version": "2.0.0",
        "node_id": NODE_ID,
        "db_epoch": db_epoch,
        "run_id": run_id,
        "table": "lightning_events",
        "cursor": {"strategy": "append", "last_edge_id": 0},
        "rows": [
            {
                "edge_id": 1,
                "ts_pi_utc": "2026-05-30T03:15:42Z",
                "event_type": "disturber",
                "created_at_utc": "2026-05-30T03:15:42Z",
            },
            {
                "edge_id": 2,
                "ts_pi_utc": "2026-05-30T03:15:43Z",
                "event_type": "meteor",
                "created_at_utc": "2026-05-30T03:15:43Z",
            },
            {
                "edge_id": 3,
                "ts_pi_utc": "2026-05-30T03:15:44Z",
                "event_type": "lightning",
                "created_at_utc": "2026-05-30T03:15:44Z",
            },
        ],
    }


def test_poison_row_quarantined_cursor_advances(client, session):
    from sqlalchemy import func, select

    from app.models.lightning import LightningEvent

    r = client.post(
        "/api/ingest/sync-batch",
        json=_envelope_with_poison(new_db_epoch(), new_run_id()),
        headers=auth_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["accepted"] == 2
    assert len(body["rejected"]) == 1
    assert body["rejected"][0]["index"] == 1
    assert body["status"] == "partial"

    assert body["accepted_cursor"]["last_edge_id"] == 3

    count = session.execute(
        select(func.count()).select_from(LightningEvent)
    ).scalar_one()
    assert count == 2
