from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import NODE_ID, NODE_TOKEN

SECOND_NODE_ID = "rpi-test-02"
SECOND_NODE_TOKEN = "second-test-token-secret"


@pytest.fixture(autouse=True)
def _enable_test_only_siren_access(client, monkeypatch):
    monkeypatch.setattr("app.settings.settings.siren_audit_enabled", True)
    monkeypatch.setattr("app.settings.settings.admin_auth_mode", "api_key")
    monkeypatch.setattr("app.settings.settings.admin_api_key", "test-admin-key")
    client.headers.update({"X-API-Key": "test-admin-key"})


def _configure_ready_node(session) -> None:
    from app.models.registry import EdgeNode

    node = session.query(EdgeNode).filter_by(node_id=NODE_ID).one()
    node.last_seen_utc = datetime.now(timezone.utc)
    node.enabled = True
    session.commit()


def _configure_operators(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.settings.settings.siren_audit_operators_json",
        '[{"id":"ops-1","name":"Operator Lab","role":"operator"},{"id":"admin-1","name":"Admin Lab","role":"admin"}]',
    )


def test_siren_audit_options_returns_nodes_and_operators(client, session, monkeypatch):
    _configure_ready_node(session)
    _configure_operators(monkeypatch)

    r = client.get("/api/siren/audit-test/options")
    assert r.status_code == 200
    body = r.json()
    assert body["operators"][0]["id"] == "api-key-admin"
    assert any(item["nodeId"] == NODE_ID for item in body["nodes"])
    assert body["limits"]["cooldownSeconds"] == 60


def test_siren_audit_create_ignores_client_requested_by(client, session, monkeypatch):
    _configure_ready_node(session)
    _configure_operators(monkeypatch)

    r = client.post(
        "/api/siren/audit-test",
        json={
            "nodeId": NODE_ID,
            "requestedBy": "stranger",
            "durationSec": 2,
            "repeats": 1,
            "gapSec": 1,
            "reason": "uji relay",
        },
    )
    assert r.status_code == 200
    assert r.json()["requestedBy"] == "api-key-admin"
    assert r.json()["requestedRole"] == "admin"


def test_siren_audit_create_validates_duration(client, session, monkeypatch):
    _configure_ready_node(session)
    _configure_operators(monkeypatch)

    r = client.post(
        "/api/siren/audit-test",
        json={
            "nodeId": NODE_ID,
            "requestedBy": "ops-1",
            "durationSec": 99,
            "repeats": 1,
            "gapSec": 1,
            "reason": "uji relay",
        },
    )
    assert r.status_code == 422


def test_siren_audit_create_and_cooldown(client, session, monkeypatch):
    _configure_ready_node(session)
    _configure_operators(monkeypatch)

    payload = {
        "nodeId": NODE_ID,
        "requestedBy": "ops-1",
        "durationSec": 2,
        "repeats": 2,
        "gapSec": 1,
        "reason": "uji bunyi sirine",
    }
    r1 = client.post("/api/siren/audit-test", json=payload)
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["status"] == "queued"
    assert body1["command"]["type"] == "siren_audit_test"
    assert body1["requestedRole"] == "admin"

    r2 = client.post("/api/siren/audit-test", json=payload)
    assert r2.status_code == 409
    body2 = r2.json()
    assert body2["error"]["code"] == "SIREN_COOLDOWN_ACTIVE"
    assert body2["cooldownRemainingSeconds"] > 0


def test_siren_audit_pending_command_and_success_callback(client, session, monkeypatch):
    _configure_ready_node(session)
    _configure_operators(monkeypatch)

    create = client.post(
        "/api/siren/audit-test",
        json={
            "nodeId": NODE_ID,
            "requestedBy": "admin-1",
            "durationSec": 1.5,
            "repeats": 1,
            "gapSec": 0,
            "reason": "uji pasca maintenance",
        },
    )
    assert create.status_code == 200
    request_id = create.json()["requestId"]

    # Machine routes must remain independent from browser/admin authentication.
    admin_key = client.headers.pop("X-API-Key")
    pending = client.get(
        "/api/siren/commands/pending",
        headers={"Authorization": f"Bearer {NODE_TOKEN}"},
    )
    assert pending.status_code == 200
    pending_body = pending.json()
    assert pending_body["items"][0]["requestId"] == request_id
    assert pending_body["items"][0]["status"] == "dispatched"

    executed_at = datetime.now(timezone.utc).isoformat()
    callback = client.post(
        "/api/siren/audit-test/status",
        json={
            "requestId": request_id,
            "nodeId": NODE_ID,
            "status": "success",
            "executedAt": executed_at,
            "message": "sirine berbunyi normal",
            "details": {"relay": "ok"},
        },
        headers={"Authorization": f"Bearer {NODE_TOKEN}"},
    )
    assert callback.status_code == 200
    callback_body = callback.json()
    assert callback_body["status"] == "success"
    assert callback_body["message"] == "sirine berbunyi normal"

    client.headers["X-API-Key"] = admin_key
    latest = client.get(f"/api/siren/audit-test/latest?node={NODE_ID}")
    assert latest.status_code == 200
    latest_body = latest.json()
    assert latest_body["latest"]["status"] == "success"
    assert latest_body["statusUpdates"][0]["status"] == "success"


def test_siren_machine_routes_reject_cross_node_access(client, session, monkeypatch):
    from app.ingest.auth import hash_token
    from app.models.registry import EdgeNode

    _configure_ready_node(session)
    _configure_operators(monkeypatch)
    session.add(
        EdgeNode(
            node_id=SECOND_NODE_ID,
            name="second test node",
            api_token_hash=hash_token(SECOND_NODE_TOKEN),
            enabled=True,
        )
    )
    session.commit()

    create = client.post(
        "/api/siren/audit-test",
        json={
            "nodeId": NODE_ID,
            "durationSec": 1,
            "repeats": 1,
            "gapSec": 0,
            "reason": "cross-node isolation regression",
        },
    )
    assert create.status_code == 200
    request_id = create.json()["requestId"]
    client.headers.pop("X-API-Key")

    second_poll = client.get(
        "/api/siren/commands/pending",
        headers={"Authorization": f"Bearer {SECOND_NODE_TOKEN}"},
    )
    assert second_poll.status_code == 200
    assert second_poll.json()["items"] == []

    second_node_callback = client.post(
        "/api/siren/audit-test/status",
        json={
            "requestId": request_id,
            "nodeId": NODE_ID,
            "status": "acknowledged",
        },
        headers={"Authorization": f"Bearer {SECOND_NODE_TOKEN}"},
    )
    assert second_node_callback.status_code == 409
    assert second_node_callback.json()["error"]["code"] == "SIREN_NODE_MISMATCH"

    mismatched_body_callback = client.post(
        "/api/siren/audit-test/status",
        json={
            "requestId": request_id,
            "nodeId": SECOND_NODE_ID,
            "status": "acknowledged",
        },
        headers={"Authorization": f"Bearer {NODE_TOKEN}"},
    )
    assert mismatched_body_callback.status_code == 409
    assert mismatched_body_callback.json()["error"]["code"] == "SIREN_NODE_MISMATCH"


def test_siren_audit_requires_admin_auth_even_when_dashboard_auth_is_public(client, session, monkeypatch):
    _configure_ready_node(session)
    _configure_operators(monkeypatch)
    client.headers.pop("X-API-Key", None)
    r = client.get("/api/siren/audit-test/options")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"

    ok = client.get("/api/siren/audit-test/options", headers={"X-API-Key": "test-admin-key"})
    assert ok.status_code == 200


def test_siren_audit_history_filters_by_status(client, session, monkeypatch):
    _configure_ready_node(session)
    _configure_operators(monkeypatch)

    create = client.post(
        "/api/siren/audit-test",
        json={
            "nodeId": NODE_ID,
            "requestedBy": "admin-1",
            "durationSec": 1,
            "repeats": 1,
            "gapSec": 0,
            "reason": "uji riwayat",
        },
    )
    request_id = create.json()["requestId"]

    callback = client.post(
        "/api/siren/audit-test/status",
        json={
            "requestId": request_id,
            "nodeId": NODE_ID,
            "status": "failed",
            "executedAt": (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
            "message": "relay timeout",
            "details": {"relay": "timeout"},
        },
        headers={"Authorization": f"Bearer {NODE_TOKEN}"},
    )
    assert callback.status_code == 200

    history = client.get("/api/siren/audit-test/history?status=failed&page=1&page_size=5")
    assert history.status_code == 200
    body = history.json()
    assert body["items"][0]["status"] == "failed"
    assert body["meta"]["total_items"] >= 1
