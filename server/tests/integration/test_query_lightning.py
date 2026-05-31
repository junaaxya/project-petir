from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from tests.conftest import NODE_ID


def _seed_run(session, epoch):
    from app.models.registry import SyncRun

    run_id = uuid.uuid4()
    session.add(SyncRun(run_id=run_id, node_id=NODE_ID, status="accepted"))
    session.commit()
    return run_id


def _seed_lightning_summaries(session, count: int = 5):
    from app.models.lightning import LightningMinuteSummary

    base = datetime(2026, 5, 30, 10, 0, tzinfo=timezone.utc)
    epoch = uuid.uuid4()
    run = _seed_run(session, epoch)
    for i in range(count):
        session.add(
            LightningMinuteSummary(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                change_seq=i + 1,
                minute_utc=base + timedelta(minutes=i),
                source="arduino",
                device="as3935",
                lightning_count=2 if i % 2 == 0 else 0,
                disturber_count=1,
                noise_window_count=0,
                noise_event_count=0,
                status="activity" if i % 2 == 0 else "quiet",
                last_event_ts_utc=base + timedelta(minutes=i, seconds=15) if i % 2 == 0 else None,
                last_distance_km=12.0 if i % 2 == 0 else None,
                max_energy_raw=500 if i % 2 == 0 else None,
                updated_at_utc=base + timedelta(minutes=i, seconds=30),
            )
        )
    session.commit()
    return base


def _seed_lightning_events(session, count: int = 4):
    from app.models.lightning import LightningEvent

    base = datetime(2026, 5, 30, 10, 0, tzinfo=timezone.utc)
    epoch = uuid.uuid4()
    run = _seed_run(session, epoch)
    for i in range(count):
        session.add(
            LightningEvent(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=100 + i,
                ts_pi_utc=base + timedelta(seconds=i * 30),
                source="arduino",
                device="as3935",
                event_type="lightning" if i % 2 == 0 else "disturber",
                distance_km=10.0 + i,
                energy_raw=400 + i * 50,
                noise_level=None,
                created_at_utc=base + timedelta(seconds=i * 30),
            )
        )
    session.commit()
    return base


def test_lightning_latest_empty(client):
    r = client.get("/api/lightning/latest")
    assert r.status_code == 200
    assert r.json()["minute"] is None


def test_lightning_latest_returns_newest(client, session):
    _seed_lightning_summaries(session, count=5)
    r = client.get("/api/lightning/latest")
    assert r.status_code == 200
    minute = r.json()["minute"]
    assert minute is not None
    assert minute["device"] == "as3935"


def test_lightning_history_empty(client):
    r = client.get("/api/lightning/history?interval=1h")
    assert r.status_code == 200
    body = r.json()
    assert body["series"] == []
    assert body["meta"]["count"] == 0


def test_lightning_history_raw(client, session):
    base = _seed_lightning_summaries(session, count=5)
    frm = (base - timedelta(minutes=1)).isoformat()
    to = (base + timedelta(hours=1)).isoformat()
    r = client.get(
        "/api/lightning/history",
        params={"interval": "raw", "from": frm, "to": to},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["downsampled"] is False
    assert body["meta"]["count"] == 5
    assert "bucket" in body["series"][0]


def test_lightning_events_empty(client):
    r = client.get("/api/lightning/events")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []


def test_lightning_events_returns_rows(client, session):
    _seed_lightning_events(session, count=4)
    r = client.get("/api/lightning/events")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["count"] == 4
    assert body["items"][0]["event_type"] in ("lightning", "disturber")


def test_lightning_events_filter_by_type(client, session):
    _seed_lightning_events(session, count=4)
    r = client.get("/api/lightning/events?event_type=lightning")
    assert r.status_code == 200
    body = r.json()
    for item in body["items"]:
        assert item["event_type"] == "lightning"
