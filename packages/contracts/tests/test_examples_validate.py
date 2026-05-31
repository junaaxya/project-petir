"""Contract self-tests: example payloads must satisfy BOTH the JSON Schema
truth and the Pydantic models. This catches drift between schema/ and python/.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from petir_contracts import ROW_MODELS, SyncBatchEnvelope, TableName

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_all_row_schemas_parse():
    files = list((SCHEMA_DIR / "rows").glob("*.json"))
    assert len(files) == len(TableName), "one row schema per table expected"
    for f in files:
        doc = _load(f)
        assert doc["type"] == "object"
        assert "properties" in doc


def test_row_models_cover_every_table():
    assert set(ROW_MODELS) == {t.value for t in TableName}


EXAMPLE_SUMMARY = {
    "contract_version": "2.0.0",
    "node_id": "rpi-lab-01",
    "db_epoch": "11111111-2222-3333-4444-555555555555",
    "run_id": "9b1c2d3e-4f50-6172-8394-a5b6c7d8e9f0",
    "run": {"started_at_utc": "2026-05-30T03:16:00Z", "duration_ms": 142, "sequence": 2},
    "table": "weather_minute_summary",
    "cursor": {"strategy": "summary", "last_change_seq": 5521},
    "rows": [
        {
            "change_seq": 5522,
            "minute_utc": "2026-05-30T03:15:00Z",
            "source": "arduino",
            "device": "weather-01",
            "sample_count": 12,
            "valid_sample_count": 12,
            "status": "ok",
            "degraded": False,
            "temperature_avg": 27.4,
            "temperature_min": 27.1,
            "temperature_max": 27.8,
            "humidity_avg": 81.2,
            "pressure_avg": 1008.6,
            "rain_max": 0.0,
            "wind_speed_avg": 1.4,
            "wind_speed_max": 2.1,
            "latest_wind_dir_deg": 135,
            "last_sample_ts_utc": "2026-05-30T03:15:55Z",
            "updated_at_utc": "2026-05-30T03:16:01Z",
        }
    ],
}

EXAMPLE_APPEND = {
    "contract_version": "2.0.0",
    "node_id": "rpi-lab-01",
    "db_epoch": "11111111-2222-3333-4444-555555555555",
    "run_id": "9b1c2d3e-4f50-6172-8394-a5b6c7d8e9f0",
    "run": {"started_at_utc": "2026-05-30T03:16:00Z", "duration_ms": 142, "sequence": 5},
    "table": "lightning_events",
    "cursor": {"strategy": "append", "last_edge_id": 318},
    "rows": [
        {
            "edge_id": 319,
            "ts_pi_utc": "2026-05-30T03:15:42Z",
            "source": "arduino",
            "device": "lightning-01",
            "sensor": "as3935",
            "event_type": "disturber",
            "distance_km": None,
            "energy_raw": 0,
            "noise_level": 2,
            "irq_source": 4,
            "raw_line": "INT=4",
            "ingest_run_id": 5521,
            "created_at_utc": "2026-05-30T03:15:42Z",
        }
    ],
}


@pytest.mark.parametrize("payload", [EXAMPLE_SUMMARY, EXAMPLE_APPEND])
def test_envelope_validates_with_pydantic(payload):
    env = SyncBatchEnvelope.model_validate(payload)
    model = ROW_MODELS[env.table.value]
    for row in env.rows:
        model.model_validate(row)


def test_extra_field_is_rejected():
    bad = json.loads(json.dumps(EXAMPLE_APPEND))
    bad["rows"][0]["unexpected_field"] = 1
    env = SyncBatchEnvelope.model_validate(bad)
    with pytest.raises(Exception):
        ROW_MODELS[env.table.value].model_validate(env.rows[0])


def test_bad_enum_is_rejected():
    bad = json.loads(json.dumps(EXAMPLE_APPEND))
    bad["rows"][0]["event_type"] = "meteor"
    env = SyncBatchEnvelope.model_validate(bad)
    with pytest.raises(Exception):
        ROW_MODELS[env.table.value].model_validate(env.rows[0])
