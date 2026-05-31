from __future__ import annotations

from tests.conftest import NODE_ID, auth_headers, new_db_epoch, new_run_id

from petir_contracts import SyncBatchEnvelope, SyncBatchResponse


def test_append_and_summary_roundtrip_through_contract(client):
    append_env = {
        "contract_version": "2.0.0",
        "node_id": NODE_ID,
        "db_epoch": new_db_epoch(),
        "run_id": new_run_id(),
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
                "energy_raw": 0,
                "noise_level": 2,
                "irq_source": 4,
                "raw_line": "INT=4",
                "ingest_run_id": 5521,
                "created_at_utc": "2026-05-30T03:15:42Z",
            }
        ],
    }
    SyncBatchEnvelope.model_validate(append_env)
    r1 = client.post("/api/ingest/sync-batch", json=append_env, headers=auth_headers())
    assert r1.status_code == 200, r1.text
    parsed1 = SyncBatchResponse.model_validate(r1.json())
    assert parsed1.accepted == 1

    summary_env = {
        "contract_version": "2.0.0",
        "node_id": NODE_ID,
        "db_epoch": new_db_epoch(),
        "run_id": new_run_id(),
        "table": "weather_minute_summary",
        "cursor": {"strategy": "summary", "last_change_seq": 5521},
        "rows": [
            {
                "change_seq": 5522,
                "minute_utc": "2026-05-30T03:15:00Z",
                "source": "arduino",
                "device": "weather-01",
                "status": "ok",
                "temperature_avg": 27.4,
                "updated_at_utc": "2026-05-30T03:16:01Z",
            }
        ],
    }
    SyncBatchEnvelope.model_validate(summary_env)
    r2 = client.post("/api/ingest/sync-batch", json=summary_env, headers=auth_headers())
    assert r2.status_code == 200, r2.text
    parsed2 = SyncBatchResponse.model_validate(r2.json())
    assert parsed2.accepted == 1
    assert parsed2.accepted_cursor.last_change_seq == 5522
