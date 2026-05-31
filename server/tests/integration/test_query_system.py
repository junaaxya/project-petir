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


def _seed_system_events(session, count: int = 6):
    from app.models.ops import SystemEvent

    base = datetime(2026, 5, 30, 8, 0, tzinfo=timezone.utc)
    epoch = uuid.uuid4()
    run = _seed_run(session, epoch)
    levels = ["info", "warn", "error", "info", "info", "critical"]
    for i in range(count):
        session.add(
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=200 + i,
                ts_pi_utc=base + timedelta(minutes=i * 5),
                source="system",
                level=levels[i % len(levels)],
                event_type="boot" if i == 0 else "heartbeat",
                message=f"Event {i}",
                created_at_utc=base + timedelta(minutes=i * 5),
            )
        )
    session.commit()
    return base


def test_system_events_empty(client):
    r = client.get("/api/system/events")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []


def test_system_events_returns_rows(client, session):
    _seed_system_events(session, count=6)
    r = client.get("/api/system/events")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["count"] == 6


def test_system_events_filter_by_level(client, session):
    _seed_system_events(session, count=6)
    r = client.get("/api/system/events?level=error")
    assert r.status_code == 200
    body = r.json()
    for item in body["items"]:
        assert item["level"] == "error"


def test_system_summary_empty(client):
    r = client.get("/api/system/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_events"] == 0
    assert body["counts_by_level"] == {}
    assert body["recent"] == []


def test_system_summary_with_data(client, session):
    _seed_system_events(session, count=6)
    r = client.get("/api/system/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_events"] == 6
    assert "info" in body["counts_by_level"]
    assert body["counts_by_level"]["info"] == 3
    assert len(body["recent"]) == 6
