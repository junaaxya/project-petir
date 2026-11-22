from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.availability_logger import (
    EVENT_NODE_OFFLINE,
    EVENT_NODE_ONLINE,
    SERVER_MONITOR_SOURCE,
    run_availability_check,
)
from app.models.ops import SystemEvent
from tests.conftest import NODE_ID


def _server_events(session):
    return session.execute(
        select(SystemEvent)
        .where(SystemEvent.source == SERVER_MONITOR_SOURCE)
        .order_by(SystemEvent.ts_pi_utc.asc())
    ).scalars().all()


def test_first_run_initializes_status_without_emitting_event(session, seeded_node):
    now = datetime.now(timezone.utc)
    seeded_node.last_seen_utc = now - timedelta(seconds=240)
    session.commit()

    result = run_availability_check(session, now=now)
    session.refresh(seeded_node)

    assert result["events_created"] == 0
    assert seeded_node.availability_status == "offline"
    assert _server_events(session) == []


def test_logs_offline_transition_once(session, seeded_node):
    now = datetime.now(timezone.utc)
    seeded_node.last_seen_utc = now
    seeded_node.availability_status = "fresh"
    session.commit()

    result = run_availability_check(session, now=now + timedelta(seconds=240))
    session.refresh(seeded_node)
    events = _server_events(session)

    assert result["events_created"] == 1
    assert seeded_node.availability_status == "offline"
    assert len(events) == 1
    assert events[0].event_type == EVENT_NODE_OFFLINE
    assert events[0].message == "Sensor cuaca offline: tidak ada data baru dari Raspberry Pi."


def test_repeated_offline_check_does_not_duplicate_event(session, seeded_node):
    now = datetime.now(timezone.utc)
    seeded_node.last_seen_utc = now
    seeded_node.availability_status = "fresh"
    session.commit()

    run_availability_check(session, now=now + timedelta(seconds=240))
    result = run_availability_check(session, now=now + timedelta(seconds=300))
    events = _server_events(session)

    assert result["events_created"] == 0
    assert len(events) == 1
    assert events[0].event_type == EVENT_NODE_OFFLINE


def test_logs_online_when_offline_node_recovers(session, seeded_node):
    now = datetime.now(timezone.utc)
    seeded_node.last_seen_utc = now
    seeded_node.availability_status = "offline"
    session.commit()

    result = run_availability_check(session, now=now)
    session.refresh(seeded_node)
    events = _server_events(session)

    assert result["events_created"] == 1
    assert seeded_node.availability_status == "fresh"
    assert len(events) == 1
    assert events[0].event_type == EVENT_NODE_ONLINE
    assert events[0].message == "Sensor cuaca online kembali: data dari Raspberry Pi kembali diterima."


def test_no_event_for_fresh_to_stale_transition(session, seeded_node):
    now = datetime.now(timezone.utc)
    seeded_node.last_seen_utc = now
    seeded_node.availability_status = "fresh"
    session.commit()

    result = run_availability_check(session, now=now + timedelta(seconds=90))
    session.refresh(seeded_node)

    assert result["events_created"] == 0
    assert seeded_node.availability_status == "stale"
    assert _server_events(session) == []


def test_admin_availability_run_returns_summary(client, session, seeded_node):
    now = datetime.now(timezone.utc)
    seeded_node.last_seen_utc = now
    seeded_node.availability_status = "fresh"
    session.commit()

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now + timedelta(seconds=240)

    import app.availability_logger as availability_logger

    original = availability_logger.datetime
    availability_logger.datetime = FrozenDateTime
    try:
        r = client.post("/api/admin/availability/run")
    finally:
        availability_logger.datetime = original

    assert r.status_code == 200
    body = r.json()
    assert body["events_created"] == 1
    assert body["transitions"][0]["node_id"] == NODE_ID
    assert body["transitions"][0]["event_type"] == EVENT_NODE_OFFLINE