from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from tests.conftest import NODE_ID


def _seed_summaries(session, count: int = 6):
    from app.models.weather import WeatherMinuteSummary

    base = datetime(2026, 5, 30, 3, 0, tzinfo=timezone.utc)
    epoch = uuid.uuid4()
    run = _seed_run(session, epoch)
    for i in range(count):
        session.add(
            WeatherMinuteSummary(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                change_seq=i + 1,
                minute_utc=base + timedelta(minutes=i),
                source="arduino",
                device="weather-01",
                sample_count=12,
                status="ok",
                temperature_avg=27.0 + i,
                temperature_min=26.0 + i,
                temperature_max=28.0 + i,
                humidity_avg=80.0,
                pressure_avg=1008.0,
                rain_max=0.0,
                wind_speed_avg=1.0,
                wind_speed_max=2.0,
                updated_at_utc=base + timedelta(minutes=i, seconds=30),
            )
        )
    session.commit()
    return base


def _seed_raw_samples(session, count: int = 6):
    from app.models.weather import WeatherSample

    base = datetime(2026, 5, 30, 3, 0, tzinfo=timezone.utc)
    epoch = uuid.uuid4()
    run = _seed_run(session, epoch)
    for i in range(count):
        session.add(
            WeatherSample(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=i + 1,
                ts_pi_utc=base + timedelta(seconds=i * 10),
                source="arduino",
                device="weather-01",
                sensor="bme280",
                temperature_c=27.5 + i,
                humidity_pct=79.0 + i,
                pressure_hpa=1007.0 + i,
                illuminance_lux=100.0 + i,
                rain_mm=0.0,
                wind_speed_ms=1.5 + i,
                wind_dir_code=2,
                wind_dir_deg=45.0,
                edge_ingest_run_id=i + 100,
                created_at_utc=base + timedelta(seconds=i * 10),
            )
        )
    session.commit()
    return base


def _seed_run(session, epoch):
    from app.models.registry import SyncRun

    run_id = uuid.uuid4()
    session.add(SyncRun(run_id=run_id, node_id=NODE_ID, status="accepted"))
    session.commit()
    return run_id


def test_latest_empty_returns_200_null(client):
    r = client.get("/api/weather/latest")
    assert r.status_code == 200
    assert r.json()["minute"] is None


def test_history_empty_range_returns_200_empty_series(client):
    r = client.get("/api/weather/history?interval=1h")
    assert r.status_code == 200
    body = r.json()
    assert body["series"] == []
    assert body["meta"]["count"] == 0


def test_latest_returns_newest_sample_when_available(client, session):
    _seed_summaries(session, count=3)
    _seed_raw_samples(session, count=6)
    r = client.get("/api/weather/latest")
    assert r.status_code == 200
    minute = r.json()["minute"]
    assert minute is not None
    assert minute["source"] == "arduino"
    assert minute["temperature_avg"] == 32.5
    assert minute["temperature_min"] == 32.5
    assert minute["temperature_max"] == 32.5
    assert minute["humidity_avg"] == 84.0
    assert minute["pressure_avg"] == 1012.0
    assert minute["illuminance_avg"] == 105.0
    assert minute["rain_max"] == 0.0
    assert minute["wind_speed_avg"] == 6.5
    assert minute["wind_speed_max"] == 6.5
    assert minute["latest_wind_dir_deg"] == 45.0
    assert minute["sample_count"] == 1


def test_latest_falls_back_to_newest_summary_when_sample_missing(client, session):
    _seed_summaries(session, count=3)
    r = client.get("/api/weather/latest")
    assert r.status_code == 200
    minute = r.json()["minute"]
    assert minute is not None
    assert minute["source"] == "arduino"
    assert minute["temperature_avg"] == 29.0


def test_history_raw_returns_all_rows(client, session):
    base = _seed_raw_samples(session, count=6)
    frm = (base - timedelta(minutes=1)).isoformat()
    to = (base + timedelta(hours=1)).isoformat()
    r = client.get(
        "/api/weather/history",
        params={"interval": "raw", "from": frm, "to": to},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["downsampled"] is False
    assert body["meta"]["count"] == 6
    first = body["series"][0]
    assert "bucket" in first
    assert "temperature_c" in first
    assert "temperature_avg" not in first


def test_history_hourly_buckets(client, session):
    base = _seed_summaries(session, count=6)
    frm = (base - timedelta(minutes=1)).isoformat()
    to = (base + timedelta(hours=2)).isoformat()
    r = client.get(
        "/api/weather/history",
        params={"interval": "1h", "from": frm, "to": to},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["downsampled"] is True
    assert body["meta"]["count"] == 1
    bucket = body["series"][0]
    assert bucket["sample_count"] == 72
    assert bucket["temperature_max"] == 33.0


def test_history_bad_range_returns_400(client):
    r = client.get(
        "/api/weather/history?interval=1h&from=2026-05-30T10:00:00Z&to=2026-05-30T09:00:00Z"
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "BAD_RANGE"


def test_quality_events_allows_long_ranges(client, session):
    base = _seed_summaries(session, count=6)
    frm = (base - timedelta(days=30)).isoformat()
    to = (base + timedelta(days=1)).isoformat()

    r30 = client.get(
        "/api/weather/quality-events",
        params={"from": frm, "to": to, "limit": 10},
    )
    assert r30.status_code == 200
    assert r30.json()["summary"]["total_minutes"] == 6

    r365 = client.get(
        "/api/weather/quality-events",
        params={
            "from": (base - timedelta(days=365)).isoformat(),
            "to": to,
            "limit": 10,
        },
    )
    assert r365.status_code == 200
    assert r365.json()["summary"]["total_minutes"] == 6


def test_health_latest_reports_streams(client, session):
    _seed_summaries(session, count=3)
    r = client.get("/api/health/latest")
    assert r.status_code == 200
    body = r.json()
    tables = {s["table"] for s in body["streams"]}
    assert "weather_minute_summary" in tables
    wms = next(s for s in body["streams"] if s["table"] == "weather_minute_summary")
    assert wms["last_ts_utc"] is not None
