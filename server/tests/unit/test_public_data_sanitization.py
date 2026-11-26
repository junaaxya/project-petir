from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace


def _weather_row():
    values = {
        "ts_pi_utc": datetime.now(timezone.utc),
        "minute_utc": datetime.now(timezone.utc),
        "source": "10.0.0.4:/dev/ttyUSB0",
        "device": "/dev/serial/by-id/internal-sensor",
        "status": "ok",
        "degraded": False,
        "sample_count": 1,
        "temperature_c": 29.0,
        "humidity_pct": 80.0,
        "pressure_hpa": 1009.0,
        "illuminance_lux": 123.0,
        "rain_mm": 0.0,
        "wind_speed_ms": 1.0,
        "wind_dir_deg": 90.0,
        "temperature_avg": 29.0,
        "temperature_min": 29.0,
        "temperature_max": 29.0,
        "humidity_avg": 80.0,
        "pressure_avg": 1009.0,
        "illuminance_avg": 123.0,
        "rain_max": 0.0,
        "wind_speed_avg": 1.0,
        "wind_speed_max": 1.0,
        "latest_wind_dir_deg": 90.0,
    }
    return SimpleNamespace(**values)


def test_weather_and_lightning_public_metadata_is_redacted(monkeypatch):
    from app.query import lightning, weather

    monkeypatch.setattr(weather.settings, "public_data_mode", "public_safe")
    monkeypatch.setattr(lightning.settings, "public_data_mode", "public_safe")

    sample = weather._sample_to_latest_dict(_weather_row())
    summary = weather._summary_to_dict(_weather_row())
    assert sample["source"] == summary["source"] == "weather_station"
    assert sample["device"] == summary["device"] == "weather_sensor"

    lightning_row = SimpleNamespace(
        node_id="public-node",
        db_epoch="2db0956d-087d-4c36-9d36-bf93f5bf3c3c",
        minute_utc=datetime.now(timezone.utc),
        source="192.168.1.5",
        device="/dev/spidev0.0",
        status="ok",
        lightning_count=1,
        disturber_count=0,
        noise_window_count=0,
        noise_event_count=0,
        last_event_ts_utc=None,
        last_distance_km=None,
        max_energy_raw=None,
        edge_id="edge-1",
        ts_pi_utc=datetime.now(timezone.utc),
        event_type="lightning",
        distance_km=5,
        energy_raw=4,
        noise_level=None,
    )
    latest = lightning._summary_to_dict(lightning_row)
    event = lightning._event_to_dict(lightning_row)
    assert latest["source"] == "lightning_station"
    assert latest["device"] == "lightning_sensor"
    assert {"source", "device", "edge_id", "energy_raw", "noise_level"}.isdisjoint(event)


def test_public_lightning_event_uses_opaque_id_and_drops_internal_fields(monkeypatch):
    from app.query import lightning

    monkeypatch.setattr(lightning.settings, "public_data_mode", "public_safe")
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        node_id="public-node",
        db_epoch="2db0956d-087d-4c36-9d36-bf93f5bf3c3c",
        edge_id=123456,
        ts_pi_utc=now,
        event_type="lightning",
        distance_km=8.0,
        energy_raw=991,
        noise_level=7,
        irq_source=31,
        raw_line="IRQ=31 register=0x3f",
        source="collector@10.0.0.4",
        device="/dev/serial/by-id/private-device",
    )

    first = lightning._event_to_dict(row)
    second = lightning._event_to_dict(row)
    assert first == second
    assert first["event_id"].startswith("evt_")
    assert set(first) == {"event_id", "ts_pi_utc", "event_type", "distance_km"}
    assert "123456" not in first["event_id"]


def test_legacy_lightning_event_preserves_existing_disclosure(monkeypatch):
    from app.query import lightning

    monkeypatch.setattr(lightning.settings, "public_data_mode", "legacy_full")
    row = SimpleNamespace(
        node_id="public-node",
        db_epoch="2db0956d-087d-4c36-9d36-bf93f5bf3c3c",
        edge_id=42,
        ts_pi_utc=datetime.now(timezone.utc),
        event_type="noise",
        distance_km=None,
        energy_raw=12,
        noise_level=3,
        source="arduino",
        device="as3935",
    )
    event = lightning._event_to_dict(row)
    assert event["edge_id"] == 42
    assert event["energy_raw"] == 12
    assert event["noise_level"] == 3
    assert event["source"] == "arduino"


def test_forecast_public_response_drops_model_and_arbitrary_details(monkeypatch):
    from app.query import forecast

    monkeypatch.setattr(forecast.settings, "public_data_mode", "public_safe")
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        forecast_type="lightning_risk",
        computed_at_utc=now,
        source_window_start_utc=now,
        source_window_end_utc=now,
        target_time_utc=now,
        horizon_minutes=30,
        score=0.7,
        value_numeric=None,
        label="high",
        confidence=0.8,
        status="ok",
        model_name="private-model",
        model_version="internal-build",
        details_json={"gateway": "10.0.0.1", "private_path": "/srv/model"},
    )
    item = forecast._forecast_to_response(row)
    assert item.model_name is None
    assert item.model_version is None
    assert item.details == {}


def test_public_health_schema_is_an_explicit_allowlist():
    from app.schemas.query import PublicHealthResponse

    assert set(PublicHealthResponse.model_fields) == {
        "station_status",
        "data_availability",
        "updated_at_utc",
        "freshness",
        "disruption",
    }
    forbidden = {"ip", "gateway", "interface", "default_routes", "wan_failover", "system_events"}
    assert set(PublicHealthResponse.model_fields).isdisjoint(forbidden)


def test_snapshot_path_cannot_escape_configured_directory(tmp_path, monkeypatch):
    from app.query import health

    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    monkeypatch.setattr(health.settings, "wan_failover_snapshot_dir", str(snapshot_dir))
    assert health._snapshot_dir_for_node("../../etc") is None
    assert health._snapshot_dir_for_node("node/child") is None
    assert health._snapshot_dir_for_node("node-1") == snapshot_dir / "node-1"
