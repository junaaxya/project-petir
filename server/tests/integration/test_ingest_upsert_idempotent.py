from __future__ import annotations

from tests.conftest import NODE_ID, auth_headers, new_db_epoch, new_run_id


def _summary_envelope(db_epoch: str, run_id: str, change_seq: int):
    return {
        "contract_version": "2.0.0",
        "node_id": NODE_ID,
        "db_epoch": db_epoch,
        "run_id": run_id,
        "table": "weather_minute_summary",
        "cursor": {"strategy": "summary", "last_change_seq": change_seq - 1},
        "rows": [
            {
                "change_seq": change_seq,
                "minute_utc": "2026-05-30T03:15:00Z",
                "source": "arduino",
                "device": "weather-01",
                "sample_count": 12,
                "status": "ok",
                "temperature_avg": 27.4,
                "updated_at_utc": "2026-05-30T03:16:01Z",
            }
        ],
    }


def test_idempotent_resend_no_duplicates(client, session):
    from sqlalchemy import func, select

    from app.models.weather import WeatherMinuteSummary

    db_epoch = new_db_epoch()
    env = _summary_envelope(db_epoch, new_run_id(), 5522)

    r1 = client.post("/api/ingest/sync-batch", json=env, headers=auth_headers())
    assert r1.status_code == 200, r1.text
    assert r1.json()["accepted"] == 1
    cursor1 = r1.json()["accepted_cursor"]["last_change_seq"]

    env2 = _summary_envelope(db_epoch, new_run_id(), 5522)
    r2 = client.post("/api/ingest/sync-batch", json=env2, headers=auth_headers())
    assert r2.status_code == 200, r2.text
    cursor2 = r2.json()["accepted_cursor"]["last_change_seq"]

    assert cursor1 == cursor2 == 5522

    count = session.execute(
        select(func.count()).select_from(WeatherMinuteSummary)
    ).scalar_one()
    assert count == 1
