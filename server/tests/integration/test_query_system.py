from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.availability_logger import SERVER_MONITOR_SOURCE
from tests.conftest import NODE_ID


@pytest.fixture(autouse=True)
def _operator_access(client, monkeypatch):
    monkeypatch.setattr("app.settings.settings.admin_auth_mode", "api_key")
    monkeypatch.setattr("app.settings.settings.operator_api_key", "test-operator-key")
    client.headers.update({"X-API-Key": "test-operator-key"})


def _seed_run(session, epoch):
    from app.models.registry import SyncRun

    run_id = uuid.uuid4()
    session.add(SyncRun(run_id=run_id, node_id=NODE_ID, status="accepted"))
    session.commit()
    return run_id


def _seed_system_events(session, count: int = 6):
    from app.models.ops import SystemEvent

    base = datetime.now(timezone.utc) - timedelta(minutes=count * 5)
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


def test_system_events_accept_month_range(client, session):
    base = _seed_system_events(session, count=6)
    r = client.get(
        "/api/system/events",
        params={
            "from": (base - timedelta(days=30)).isoformat(),
            "to": (base + timedelta(days=1)).isoformat(),
            "page_size": 2,
        },
    )
    assert r.status_code == 200
    assert r.json()["meta"]["total_items"] == 6


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


def test_system_events_include_server_monitor_rows(client, session):
    from app.models.ops import SystemEvent
    from app.settings import settings

    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    session.add(
        SystemEvent(
            node_id=NODE_ID,
            db_epoch=uuid.UUID(settings.availability_server_event_epoch),
            ingest_run_id=None,
            edge_id=999001,
            ts_pi_utc=base,
            source=SERVER_MONITOR_SOURCE,
            level="warn",
            event_type="node_offline",
            message="Sensor cuaca offline: tidak ada data baru dari Raspberry Pi.",
            created_at_utc=base,
        )
    )
    session.commit()

    r = client.get("/api/system/events")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["count"] == 1
    assert body["items"][0]["source"] == SERVER_MONITOR_SOURCE
    assert body["items"][0]["event_type"] == "node_offline"


def test_system_events_important_only_hides_heartbeat_but_keeps_status_transitions(client, session):
    from app.models.ops import SystemEvent
    from app.settings import settings

    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    epoch = uuid.uuid4()
    run = _seed_run(session, epoch)
    session.add_all(
        [
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=999100,
                ts_pi_utc=base,
                source="weather_ingest",
                level="info",
                event_type="ingest_heartbeat",
                message="weather ingest heartbeat",
                created_at_utc=base,
            ),
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=uuid.UUID(settings.availability_server_event_epoch),
                ingest_run_id=None,
                edge_id=999101,
                ts_pi_utc=base + timedelta(minutes=1),
                source=SERVER_MONITOR_SOURCE,
                level="info",
                event_type="node_online",
                message="Sensor cuaca online kembali: data dari Raspberry Pi kembali diterima.",
                created_at_utc=base + timedelta(minutes=1),
            ),
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=999102,
                ts_pi_utc=base + timedelta(minutes=2),
                source="system",
                level="warn",
                event_type="sensor_warning",
                message="Sensor warning",
                created_at_utc=base + timedelta(minutes=2),
            ),
        ]
    )
    session.commit()

    r = client.get("/api/system/events?important_only=true")
    assert r.status_code == 200
    body = r.json()
    assert [item["event_type"] for item in body["items"]] == ["sensor_warning", "node_online"]


def test_system_events_filter_by_event_group(client, session):
    from app.models.ops import SystemEvent
    from app.settings import settings

    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    epoch = uuid.uuid4()
    run = _seed_run(session, epoch)
    session.add_all(
        [
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=999200,
                ts_pi_utc=base,
                source="weather_ingest",
                level="info",
                event_type="ingest_heartbeat",
                message="weather ingest heartbeat",
                created_at_utc=base,
            ),
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=uuid.UUID(settings.availability_server_event_epoch),
                ingest_run_id=None,
                edge_id=999201,
                ts_pi_utc=base + timedelta(minutes=1),
                source=SERVER_MONITOR_SOURCE,
                level="info",
                event_type="node_online",
                message="Sensor cuaca online kembali",
                created_at_utc=base + timedelta(minutes=1),
            ),
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=999202,
                ts_pi_utc=base + timedelta(minutes=2),
                source="system",
                level="info",
                event_type="weather_non_sample_event",
                message="non sample event",
                created_at_utc=base + timedelta(minutes=2),
            ),
        ]
    )
    session.commit()

    r = client.get("/api/system/events?event_group=heartbeat")
    assert r.status_code == 200
    body = r.json()
    assert [item["event_type"] for item in body["items"]] == ["ingest_heartbeat"]

    r = client.get("/api/system/events?event_group=status")
    assert r.status_code == 200
    body = r.json()
    assert [item["event_type"] for item in body["items"]] == ["node_online"]

    r = client.get("/api/system/events?event_group=other")
    assert r.status_code == 200
    body = r.json()
    assert [item["event_type"] for item in body["items"]] == ["weather_non_sample_event"]


def test_system_events_technical_issues_hides_siren_audit_client(client, session):
    from app.models.ops import SystemEvent

    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    epoch = uuid.uuid4()
    run = _seed_run(session, epoch)
    session.add_all(
        [
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=999300,
                ts_pi_utc=base,
                source="siren_audit_client",
                level="error",
                event_type="siren_audit_poll_error",
                message="Polling siren audit command failed",
                created_at_utc=base,
            ),
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=999301,
                ts_pi_utc=base + timedelta(minutes=1),
                source="weather_ingest",
                level="error",
                event_type="weather_reader_error",
                message="Weather reader failed",
                created_at_utc=base + timedelta(minutes=1),
            ),
            SystemEvent(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=999302,
                ts_pi_utc=base + timedelta(minutes=2),
                source="siren_audit_client",
                level="info",
                event_type="siren_audit_poll_empty",
                message="No pending siren audit commands",
                created_at_utc=base + timedelta(minutes=2),
            ),
        ]
    )
    session.commit()

    r = client.get("/api/system/events?scope=technical_issues")
    assert r.status_code == 200
    body = r.json()
    assert [item["event_type"] for item in body["items"]] == ["weather_reader_error"]

    r = client.get("/api/system/events?event_group=other")
    assert r.status_code == 200
    body = r.json()
    assert [item["event_type"] for item in body["items"]] == ["weather_reader_error", "siren_audit_poll_error"]
