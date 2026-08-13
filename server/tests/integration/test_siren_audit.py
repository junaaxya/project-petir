from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.conftest import NODE_ID, NODE_TOKEN


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
    assert body["operators"][0]["id"] == "ops-1"
    assert any(item["nodeId"] == NODE_ID for item in body["nodes"])
    assert body["limits"]["cooldownSeconds"] == 60


def test_siren_audit_create_rejects_unlisted_operator(client, session, monkeypatch):
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
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "SIREN_AUDIT_FORBIDDEN"


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
    assert body1["requestedRole"] == "operator"

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

    latest = client.get(f"/api/siren/audit-test/latest?node={NODE_ID}")
    assert latest.status_code == 200
    latest_body = latest.json()
    assert latest_body["latest"]["status"] == "success"
    assert latest_body["statusUpdates"][0]["status"] == "success"


def test_siren_audit_dashboard_auth_applies_when_enabled(client, session, monkeypatch):
    _configure_ready_node(session)
    _configure_operators(monkeypatch)
    monkeypatch.setattr("app.settings.settings.dashboard_auth_enabled", True)
    monkeypatch.setattr("app.settings.settings.dashboard_api_key", "secret-key-123")

    r = client.get("/api/siren/audit-test/options")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"

    ok = client.get("/api/siren/audit-test/options", headers={"X-API-Key": "secret-key-123"})
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
