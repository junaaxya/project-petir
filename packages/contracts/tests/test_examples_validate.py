"""Contract self-tests: example payloads must satisfy BOTH the JSON Schema
truth and the Pydantic models. This catches drift between schema/ and python/.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from petir_contracts import (
    CONTRACT_VERSION,
    ROW_MODELS,
    DailyForecastResponse,
    LightningEventsExportResponse,
    LightningEventsResponse,
    SyncBatchEnvelope,
    TableName,
)

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _assert_schema_and_model_reject(schema_name: str, payload: dict, model) -> None:
    schema = _load(SCHEMA_DIR / "query" / schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    assert list(validator.iter_errors(payload)), "JSON Schema unexpectedly accepted payload"
    with pytest.raises(Exception):
        model.model_validate(payload)


def test_contract_version_matches_version_file():
    assert CONTRACT_VERSION == _load(SCHEMA_DIR / "version.json")["contract_version"]


def test_query_response_schemas_and_models_are_valid():
    event = {
        "edge_id": 42,
        "ts_pi_utc": "2026-11-21T12:00:00+00:00",
        "event_type": "lightning",
        "distance_km": 12.0,
        "energy_raw": 900,
        "noise_level": 1,
        "source": "arduino",
        "device": "as3935",
    }
    cases = [
        (
            "daily_forecast_response.json",
            {
                "node_id": None,
                "forecast_date_wib": "2026-11-21",
                "today_label": "Sabtu, 21 November 2026",
                "timezone": "Asia/Jakarta",
                "computed_at_utc": "2026-11-21T12:00:00+00:00",
                "status": "insufficient_data",
                "sample_count": 0,
                "latest_sample_utc": None,
                "items": [],
            },
            DailyForecastResponse,
        ),
        (
            "lightning_events_response.json",
            {
                "node_id": None,
                "items": [event],
                "meta": {
                    "count": 1,
                    "page": 1,
                    "page_size": 20,
                    "total_items": 1,
                    "total_pages": 1,
                    "has_prev": False,
                    "has_next": False,
                    "requested_limit": 200,
                },
            },
            LightningEventsResponse,
        ),
        (
            "lightning_events_export_response.json",
            {
                "node_id": None,
                "items": [event],
                "meta": {"count": 1, "scope": "all_filtered"},
            },
            LightningEventsExportResponse,
        ),
    ]

    for schema_name, payload, model in cases:
        schema = _load(SCHEMA_DIR / "query" / schema_name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
        assert model.model_validate(payload).items is not None


def test_query_event_enum_rejects_contract_drift():
    payload = {
        "node_id": None,
        "items": [
            {
                "edge_id": 42,
                "ts_pi_utc": "2026-11-21T12:00:00+00:00",
                "event_type": "meteor",
                "distance_km": None,
                "energy_raw": None,
                "noise_level": None,
                "source": None,
                "device": None,
            }
        ],
        "meta": {
            "count": 1,
            "page": 1,
            "page_size": 20,
            "total_items": 1,
            "total_pages": 1,
            "has_prev": False,
            "has_next": False,
        },
    }
    schema = _load(SCHEMA_DIR / "query" / "lightning_events_response.json")
    with pytest.raises(Exception):
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
    with pytest.raises(Exception):
        LightningEventsResponse.model_validate(payload)


def _daily_forecast_payload() -> dict:
    return {
        "node_id": None,
        "forecast_date_wib": "2026-11-21",
        "today_label": "Sabtu, 21 November 2026",
        "timezone": "Asia/Jakarta",
        "computed_at_utc": "2026-11-21T12:00:00+00:00",
        "status": "insufficient_data",
        "sample_count": 0,
        "latest_sample_utc": None,
        "items": [],
    }


def _lightning_events_payload() -> dict:
    return {
        "node_id": None,
        "items": [],
        "meta": {
            "count": 0,
            "page": 1,
            "page_size": 20,
            "total_items": 0,
            "total_pages": 1,
            "has_prev": False,
            "has_next": False,
        },
    }


def test_query_extra_property_is_rejected_by_schema_and_model():
    payload = _daily_forecast_payload()
    payload["unexpected"] = True
    _assert_schema_and_model_reject(
        "daily_forecast_response.json", payload, DailyForecastResponse
    )


def test_daily_forecast_negative_sample_count_matches_schema():
    payload = _daily_forecast_payload()
    payload["sample_count"] = -1
    _assert_schema_and_model_reject(
        "daily_forecast_response.json", payload, DailyForecastResponse
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [("count", -1), ("page", 0), ("page_size", 0), ("total_items", -1)],
)
def test_pagination_constraints_match_schema(field, value):
    payload = _lightning_events_payload()
    payload["meta"][field] = value
    _assert_schema_and_model_reject(
        "lightning_events_response.json", payload, LightningEventsResponse
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("forecast_date_wib", "21-11-2026"),
        ("forecast_date_wib", 1_700_000_000),
        ("computed_at_utc", "not-a-datetime"),
        ("computed_at_utc", 1_700_000_000),
        ("latest_sample_utc", "2026-13-99T99:99:99Z"),
    ],
)
def test_daily_forecast_date_formats_match_schema(field, value):
    payload = _daily_forecast_payload()
    payload[field] = value
    _assert_schema_and_model_reject(
        "daily_forecast_response.json", payload, DailyForecastResponse
    )


def test_lightning_event_datetime_format_matches_schema():
    payload = _lightning_events_payload()
    payload["items"] = [
        {
            "edge_id": 1,
            "ts_pi_utc": "not-a-datetime",
            "event_type": None,
            "distance_km": None,
            "energy_raw": None,
            "noise_level": None,
            "source": None,
            "device": None,
        }
    ]
    _assert_schema_and_model_reject(
        "lightning_events_response.json", payload, LightningEventsResponse
    )


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


@pytest.mark.parametrize(
    ("envelope", "field", "value"),
    [
        (EXAMPLE_APPEND, "edge_id", 0),
        (EXAMPLE_APPEND, "ts_pi_utc", "not-a-datetime"),
        (EXAMPLE_APPEND, "ts_pi_utc", 1_700_000_000),
        (EXAMPLE_SUMMARY, "change_seq", 0),
        (EXAMPLE_SUMMARY, "minute_utc", "not-a-datetime"),
        (EXAMPLE_SUMMARY, "minute_utc", 1_700_000_000),
    ],
)
def test_row_schema_and_pydantic_reject_invalid_cursor_or_datetime(
    envelope, field, value
):
    row = json.loads(json.dumps(envelope["rows"][0]))
    row[field] = value
    table = envelope["table"]
    schema = _load(SCHEMA_DIR / "rows" / f"{table}.json")
    registry = Registry().with_resource(
        "petir:enums", Resource.from_contents(_load(SCHEMA_DIR / "enums.json"))
    )
    validator = Draft202012Validator(
        schema, registry=registry, format_checker=FormatChecker()
    )
    assert list(validator.iter_errors(row)), "JSON Schema unexpectedly accepted row"
    with pytest.raises(Exception):
        ROW_MODELS[table].model_validate(row)


def test_extra_field_is_rejected():
    bad = json.loads(json.dumps(EXAMPLE_APPEND))
    bad["rows"][0]["unexpected_field"] = 1
    env = SyncBatchEnvelope.model_validate(bad)
    with pytest.raises(Exception):
        ROW_MODELS[env.table.value].model_validate(env.rows[0])


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("db_epoch",), "not-a-uuid"),
        (("run_id",), "not-a-uuid"),
        (("cursor", "last_edge_id"), -1),
        (("run", "duration_ms"), -1),
        (("run", "sequence"), 0),
        (("run", "started_at_utc"), 1_700_000_000),
    ],
)
def test_envelope_constraints_reject_invalid_values(path, value):
    bad = json.loads(json.dumps(EXAMPLE_APPEND))
    target = bad
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(Exception):
        SyncBatchEnvelope.model_validate(bad)


def test_bad_enum_is_rejected():
    bad = json.loads(json.dumps(EXAMPLE_APPEND))
    bad["rows"][0]["event_type"] = "meteor"
    env = SyncBatchEnvelope.model_validate(bad)
    with pytest.raises(Exception):
        ROW_MODELS[env.table.value].model_validate(env.rows[0])
