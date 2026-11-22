from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

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


def _add_raw_wind_samples(session, base, readings):
    """Add (seconds, speed, direction) readings for direction aggregation tests."""
    from app.models.weather import WeatherSample

    epoch = uuid.uuid4()
    run = _seed_run(session, epoch)
    for i, (seconds, speed, direction) in enumerate(readings, start=1000):
        ts = base + timedelta(seconds=seconds)
        session.add(
            WeatherSample(
                node_id=NODE_ID,
                db_epoch=epoch,
                ingest_run_id=run,
                edge_id=i,
                ts_pi_utc=ts,
                source="arduino",
                device="weather-01",
                sensor="wind",
                wind_speed_ms=speed,
                wind_dir_deg=direction,
                edge_ingest_run_id=i,
                created_at_utc=ts,
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


def test_history_keeps_zero_degree_direction_only_when_wind_is_measured(client, session):
    from app.models.weather import WeatherMinuteSummary

    base = _seed_summaries(session, count=2)
    rows = list(
        session.execute(
            select(WeatherMinuteSummary).order_by(WeatherMinuteSummary.minute_utc.asc())
        ).scalars()
    )
    rows[0].latest_wind_dir_deg = 0.0
    rows[0].wind_speed_avg = 0.4
    rows[0].wind_speed_max = 0.8
    rows[1].latest_wind_dir_deg = 180.0
    rows[1].wind_speed_avg = 0.0
    rows[1].wind_speed_max = 0.0
    session.commit()

    _add_raw_wind_samples(
        session,
        base,
        [
            (5, 0.4, 0.0),
            (65, 0.0, 180.0),
        ],
    )

    r = client.get(
        "/api/weather/history",
        params={
            "interval": "1m",
            "from": (base - timedelta(minutes=1)).isoformat(),
            "to": (base + timedelta(minutes=3)).isoformat(),
        },
    )

    assert r.status_code == 200
    series = r.json()["series"]
    assert series[0]["latest_wind_dir_deg"] == 0.0
    assert series[1]["latest_wind_dir_deg"] is None


@pytest.mark.parametrize("interval", ["1m", "5m", "15m", "1h"])
def test_history_uses_dominant_non_calm_direction_for_every_interval(
    client, session, interval
):
    from app.models.weather import WeatherMinuteSummary

    base = _seed_summaries(session, count=1)
    summary = session.execute(select(WeatherMinuteSummary)).scalar_one()
    # The legacy summary says North because its final raw sample was calm.
    summary.latest_wind_dir_deg = 0.0
    summary.wind_speed_avg = 0.5
    summary.wind_speed_max = 1.0
    session.commit()

    # Southeast is the dominant measured direction. Calm 0-degree samples must
    # not inflate North in any bucket size.
    _add_raw_wind_samples(
        session,
        base,
        [
            (5, 1.0, 135.0),
            (15, 0.8, 135.0),
            (25, 0.6, 135.0),
            (35, 0.7, 225.0),
            (45, 0.0, 0.0),
            (55, 0.0, 0.0),
        ],
    )

    r = client.get(
        "/api/weather/history",
        params={
            "interval": interval,
            "from": (base - timedelta(seconds=1)).isoformat(),
            "to": (base + timedelta(minutes=1)).isoformat(),
        },
    )

    assert r.status_code == 200
    assert r.json()["series"][0]["latest_wind_dir_deg"] == 135.0


def test_long_history_uses_summary_direction_without_raw_samples(client, session):
    from app.models.weather import WeatherMinuteSummary

    base = _seed_summaries(session, count=3)
    rows = list(session.execute(select(WeatherMinuteSummary)).scalars())
    for row in rows:
        row.latest_wind_dir_deg = 225.0
        row.wind_speed_avg = 1.0
    session.commit()

    response = client.get(
        "/api/weather/history",
        params={
            "interval": "1h",
            "from": (base - timedelta(days=30)).isoformat(),
            "to": (base + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json()["series"][0]["latest_wind_dir_deg"] == 225.0


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
