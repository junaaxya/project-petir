from __future__ import annotations

import json
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


def test_health_latest_wan_failover_fallback_when_snapshot_missing(client):
    r = client.get("/api/health/latest")
    assert r.status_code == 200
    body = r.json()
    wan = body["wan_failover"]

    assert wan["available"] is False
    assert wan["primary_badge"] == "unknown"
    assert wan["message"] == "WAN failover status belum tersedia"
    assert wan["recent_events"] == []


def test_health_latest_reads_wan_failover_snapshot(client, monkeypatch, tmp_path):
    node_dir = tmp_path / NODE_ID
    node_dir.mkdir(parents=True)
    (node_dir / "wan_failover_status.json").write_text(
        json.dumps(
            {
                "ts_utc": "2026-08-12T01:02:03Z",
                "mode": "prefer_eth",
                "active_uplink_iface": "eth0",
                "active_uplink_kind": "ethernet",
                "decision": {
                    "eth_fail_count": 0,
                    "eth_recover_count": 2,
                    "fail_threshold": 3,
                    "recover_threshold": 2,
                    "last_change": "2026-08-12T00:59:00Z",
                    "last_event": "recover_to_ethernet",
                },
                "checks": {
                    "eth": {
                        "iface": "eth0",
                        "connection": "wired",
                        "ipv4": "192.168.1.20",
                        "gateway": "192.168.1.1",
                        "ok": True,
                        "detail": "ping ok",
                        "route_metric": 100,
                    },
                    "wifi": {
                        "iface": "wlan0",
                        "connection": "ssid-lab",
                        "ipv4": "192.168.1.30",
                        "gateway": "192.168.1.1",
                        "ok": True,
                        "detail": "standby",
                        "route_metric": 600,
                    },
                },
                "default_routes": [
                    {"iface": "eth0", "gateway": "192.168.1.1", "metric": 100, "kind": "ethernet"}
                ],
                "frontend_summary": {
                    "badge": "ethernet-primary",
                    "message": "Ethernet aktif sebagai uplink utama",
                    "recommended_color": "green",
                },
            }
        ),
        encoding="utf-8",
    )
    (node_dir / "wan_failover_events_recent.json").write_text(
        json.dumps(
            [
                {
                    "ts_utc": "2026-08-12T00:59:00Z",
                    "event_type": "recover_to_ethernet",
                    "active_uplink_iface": "eth0",
                    "active_uplink_kind": "ethernet",
                    "message": "Recovered to ethernet",
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("app.query.health.settings.wan_failover_snapshot_dir", str(tmp_path))

    r = client.get("/api/health/latest")
    assert r.status_code == 200
    body = r.json()
    wan = body["wan_failover"]

    assert wan["available"] is True
    assert wan["primary_badge"] == "ethernet-primary"
    assert wan["active_uplink_iface"] == "eth0"
    assert wan["active_uplink_kind"] == "ethernet"
    assert wan["decision"]["last_event"] == "recover_to_ethernet"
    assert wan["checks"]["eth"]["ok"] is True
    assert wan["checks"]["wifi"]["route_metric"] == 600
    assert wan["recent_events"][0]["event_type"] == "recover_to_ethernet"
