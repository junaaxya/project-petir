from __future__ import annotations

import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import NODE_ID, NODE_TOKEN


def test_dashboard_auth_disabled_allows_access(client):
    r = client.get("/api/weather/latest")
    assert r.status_code == 200


def test_dashboard_auth_enabled_rejects_no_key(client, monkeypatch):
    monkeypatch.setattr("app.settings.settings.dashboard_auth_enabled", True)
    monkeypatch.setattr("app.settings.settings.dashboard_api_key", "secret-key-123")
    r = client.get("/api/weather/latest")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_dashboard_auth_enabled_rejects_wrong_key(client, monkeypatch):
    monkeypatch.setattr("app.settings.settings.dashboard_auth_enabled", True)
    monkeypatch.setattr("app.settings.settings.dashboard_api_key", "secret-key-123")
    r = client.get("/api/weather/latest", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_dashboard_auth_enabled_accepts_correct_key(client, monkeypatch):
    monkeypatch.setattr("app.settings.settings.dashboard_auth_enabled", True)
    monkeypatch.setattr("app.settings.settings.dashboard_api_key", "secret-key-123")
    r = client.get("/api/weather/latest", headers={"X-API-Key": "secret-key-123"})
    assert r.status_code == 200


def test_rate_limit_blocks_after_threshold(client, session, monkeypatch):
    monkeypatch.setattr("app.settings.settings.rate_limit_per_node", 2)
    monkeypatch.setattr("app.settings.settings.rate_limit_window_seconds", 60)

    from app.ingest.auth import _ingest_limiter
    _ingest_limiter._max = 2
    _ingest_limiter._window = 60
    _ingest_limiter._buckets.clear()

    headers = {"Authorization": f"Bearer {NODE_TOKEN}"}
    db_epoch = str(uuid.uuid4())
    envelope = {
        "contract_version": "2.0.0",
        "node_id": NODE_ID,
        "db_epoch": db_epoch,
        "run_id": str(uuid.uuid4()),
        "table": "system_events",
        "cursor": {"strategy": "append", "last_edge_id": 0},
        "rows": [{"edge_id": 1, "ts_pi_utc": "2026-05-30T10:00:00Z", "source": "sys", "level": "info", "event_type": "boot", "message": "ok", "created_at_utc": "2026-05-30T10:00:00Z"}],
    }

    r1 = client.post("/api/ingest/sync-batch", json=envelope, headers=headers)
    assert r1.status_code == 200

    envelope["run_id"] = str(uuid.uuid4())
    envelope["rows"][0]["edge_id"] = 2
    r2 = client.post("/api/ingest/sync-batch", json=envelope, headers=headers)
    assert r2.status_code == 200

    envelope["run_id"] = str(uuid.uuid4())
    envelope["rows"][0]["edge_id"] = 3
    r3 = client.post("/api/ingest/sync-batch", json=envelope, headers=headers)
    assert r3.status_code == 429
    assert r3.json()["error"]["code"] == "BACKPRESSURE"

    _ingest_limiter._buckets.clear()


def test_token_rotation_old_token_still_works(client, session):
    from app.ingest.auth import _ingest_limiter
    _ingest_limiter._buckets.clear()

    from app.models.registry import EdgeNode

    old_hash = hashlib.sha256(b"old-token").hexdigest()
    new_hash = hashlib.sha256(b"new-token").hexdigest()

    node = session.query(EdgeNode).filter_by(node_id=NODE_ID).one()
    node.api_token_hash = new_hash
    node.previous_token_hash = old_hash
    session.commit()

    envelope = {
        "contract_version": "2.0.0",
        "node_id": NODE_ID,
        "db_epoch": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "table": "system_events",
        "cursor": {"strategy": "append", "last_edge_id": 0},
        "rows": [{"edge_id": 50, "ts_pi_utc": "2026-05-30T10:00:00Z", "source": "sys", "level": "info", "event_type": "boot", "message": "ok", "created_at_utc": "2026-05-30T10:00:00Z"}],
    }

    r = client.post(
        "/api/ingest/sync-batch",
        json=envelope,
        headers={"Authorization": "Bearer old-token"},
    )
    assert r.status_code == 200
