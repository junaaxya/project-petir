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


def test_health_latest_separates_node_and_stream_freshness(client, session, seeded_node):
    from app.models.lightning import LightningMinuteSummary
    from app.models.ops import SystemEvent
    from app.models.weather import WeatherMinuteSummary

    now = datetime.now(timezone.utc)
    epoch = uuid.uuid4()
    run_id = _seed_run(session, epoch)
    seeded_node.last_seen_utc = now - timedelta(seconds=90)
    session.add(
        WeatherMinuteSummary(
            node_id=NODE_ID,
            db_epoch=epoch,
            ingest_run_id=run_id,
            change_seq=1,
            minute_utc=now - timedelta(seconds=180),
            source="arduino",
            device="weather-01",
            sample_count=12,
            status="ok",
            updated_at_utc=now - timedelta(seconds=150),
        )
    )
    session.add(
        LightningMinuteSummary(
            node_id=NODE_ID,
            db_epoch=epoch,
            ingest_run_id=run_id,
            change_seq=2,
            minute_utc=now - timedelta(hours=8),
            source="as3935",
            device="lightning-01",
            lightning_count=0,
            disturber_count=0,
            noise_window_count=0,
            noise_event_count=0,
            status="quiet",
            updated_at_utc=now - timedelta(hours=8),
        )
    )
    session.add(
        SystemEvent(
            node_id=NODE_ID,
            db_epoch=epoch,
            ingest_run_id=run_id,
            edge_id=10,
            ts_pi_utc=now - timedelta(hours=12),
            source="system",
            level="info",
            event_type="boot",
            message="booted",
            created_at_utc=now - timedelta(hours=12),
        )
    )
    session.commit()

    r = client.get("/api/health/latest")
    assert r.status_code == 200
    body = r.json()
    streams = {stream["table"]: stream for stream in body["streams"]}

    assert body["node_status"] == "stale"
    assert streams["weather_minute_summary"]["kind"] == "cadence"
    assert streams["weather_minute_summary"]["status"] == "stale"
    assert streams["lightning_minute_summary"]["kind"] == "event"
    assert streams["lightning_minute_summary"]["status"] == "idle"
    assert streams["system_events"]["kind"] == "event"
    assert streams["system_events"]["status"] == "idle"


def test_event_streams_become_unknown_when_node_is_offline(client, session, seeded_node):
    from app.models.lightning import LightningMinuteSummary

    now = datetime.now(timezone.utc)
    epoch = uuid.uuid4()
    run_id = _seed_run(session, epoch)
    seeded_node.last_seen_utc = now - timedelta(seconds=240)
    session.add(
        LightningMinuteSummary(
            node_id=NODE_ID,
            db_epoch=epoch,
            ingest_run_id=run_id,
            change_seq=1,
            minute_utc=now - timedelta(hours=2),
            source="as3935",
            device="lightning-01",
            lightning_count=0,
            disturber_count=0,
            noise_window_count=0,
            noise_event_count=0,
            status="quiet",
            updated_at_utc=now - timedelta(hours=2),
        )
    )
    session.commit()

    r = client.get("/api/health/latest")
    assert r.status_code == 200
    body = r.json()
    streams = {stream["table"]: stream for stream in body["streams"]}

    assert body["node_status"] == "offline"
    assert streams["lightning_minute_summary"]["status"] == "unknown"
    assert streams["lightning_minute_summary"]["status"] != "offline"
