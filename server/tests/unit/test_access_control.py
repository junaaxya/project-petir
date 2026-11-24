from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException


def _set_admin_mode(monkeypatch, mode: str) -> None:
    monkeypatch.setattr("app.settings.settings.admin_auth_mode", mode)
    monkeypatch.setattr("app.settings.settings.admin_api_key", "admin-secret")
    monkeypatch.setattr("app.settings.settings.operator_api_key", "operator-secret")
    monkeypatch.setattr(
        "app.settings.settings.cloudflare_access_admin_emails",
        "admin@example.com",
    )
    monkeypatch.setattr(
        "app.settings.settings.cloudflare_access_operator_emails",
        "operator@example.com",
    )


def test_admin_guard_fails_closed_when_mode_disabled(monkeypatch):
    from app.query.auth import verify_admin_user

    _set_admin_mode(monkeypatch, "disabled")
    with pytest.raises(HTTPException) as exc:
        verify_admin_user(x_api_key=None, cf_access_jwt_assertion=None)
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "ACCESS_CONTROL_NOT_CONFIGURED"


def test_api_key_roles_are_enforced(monkeypatch):
    from app.query.auth import verify_admin_user, verify_operator_user

    _set_admin_mode(monkeypatch, "api_key")
    operator = verify_operator_user(
        x_api_key="operator-secret", cf_access_jwt_assertion=None
    )
    assert operator.role == "operator"

    with pytest.raises(HTTPException) as exc:
        verify_admin_user(x_api_key="operator-secret", cf_access_jwt_assertion=None)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "FORBIDDEN"

    admin = verify_admin_user(x_api_key="admin-secret", cf_access_jwt_assertion=None)
    assert admin.role == "admin"
    assert admin.auth_method == "api_key"


def test_explicit_legacy_mode_preserves_petir1_dashboard_behavior(monkeypatch):
    from app.query.auth import verify_admin_user

    _set_admin_mode(monkeypatch, "legacy_dashboard")
    monkeypatch.setattr("app.settings.settings.dashboard_auth_enabled", False)
    principal = verify_admin_user(x_api_key=None, cf_access_jwt_assertion=None)
    assert principal.role == "admin"
    assert principal.auth_method == "legacy_dashboard"


def test_dashboard_key_is_never_promoted_in_api_key_mode(monkeypatch):
    from app.query.auth import verify_admin_user

    _set_admin_mode(monkeypatch, "api_key")
    monkeypatch.setattr("app.settings.settings.dashboard_auth_enabled", True)
    monkeypatch.setattr("app.settings.settings.dashboard_api_key", "dashboard-read-key")
    with pytest.raises(HTTPException) as exc:
        verify_admin_user(
            x_api_key="dashboard-read-key", cf_access_jwt_assertion=None
        )
    assert exc.value.status_code == 401


def test_overlapping_api_role_keys_fail_closed(monkeypatch):
    from app.query.auth import verify_operator_user

    _set_admin_mode(monkeypatch, "api_key")
    monkeypatch.setattr("app.settings.settings.admin_api_key", "same-key")
    monkeypatch.setattr("app.settings.settings.operator_api_key", "same-key")
    with pytest.raises(HTTPException) as exc:
        verify_operator_user(x_api_key="same-key", cf_access_jwt_assertion=None)
    assert exc.value.status_code == 503
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "ACCESS_CONTROL_CONFIG_INVALID"


def test_cloudflare_access_identity_and_role_are_server_derived(monkeypatch):
    from app.query import auth

    _set_admin_mode(monkeypatch, "cloudflare_access")
    monkeypatch.setattr(
        auth,
        "_decode_cloudflare_access_token",
        lambda token: {
            "sub": "cf-subject",
            "email": " Admin@Example.com ",
            "aud": ["expected-audience"],
        },
    )

    principal = auth.verify_admin_user(
        x_api_key=None, cf_access_jwt_assertion="signed-token"
    )
    assert principal.subject == "admin@example.com"
    assert principal.role == "admin"
    assert principal.auth_method == "cloudflare_access"


def test_overlapping_cloudflare_role_allowlists_fail_closed(monkeypatch):
    from app.query import auth

    _set_admin_mode(monkeypatch, "cloudflare_access")
    monkeypatch.setattr(
        "app.settings.settings.cloudflare_access_admin_emails", "same@example.com"
    )
    monkeypatch.setattr(
        "app.settings.settings.cloudflare_access_operator_emails", "same@example.com"
    )
    monkeypatch.setattr(
        auth,
        "_decode_cloudflare_access_token",
        lambda _: {"sub": "subject", "email": "same@example.com"},
    )
    with pytest.raises(HTTPException) as exc:
        auth.verify_operator_user(
            x_api_key=None, cf_access_jwt_assertion="signed-token"
        )
    assert exc.value.status_code == 503
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "ACCESS_CONTROL_CONFIG_INVALID"


def test_cloudflare_access_rejects_unlisted_identity(monkeypatch):
    from app.query import auth

    _set_admin_mode(monkeypatch, "cloudflare_access")
    monkeypatch.setattr(
        auth,
        "_decode_cloudflare_access_token",
        lambda token: {"sub": "cf-subject", "email": "stranger@example.com"},
    )

    with pytest.raises(HTTPException) as exc:
        auth.verify_operator_user(
            x_api_key=None, cf_access_jwt_assertion="signed-token"
        )
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "FORBIDDEN"


def test_siren_feature_flag_is_fail_closed(monkeypatch):
    from app.query.auth import require_siren_enabled

    monkeypatch.setattr("app.settings.settings.siren_audit_enabled", False)
    with pytest.raises(HTTPException) as exc:
        require_siren_enabled()
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "SIREN_DISABLED"

    monkeypatch.setattr("app.settings.settings.siren_audit_enabled", True)
    assert require_siren_enabled() is None


def test_cloudflare_decoder_requires_expected_signature_claims(monkeypatch):
    from app.query import auth

    monkeypatch.setattr(
        "app.settings.settings.cloudflare_access_team_domain",
        "petirlabs.cloudflareaccess.com",
    )
    monkeypatch.setattr(
        "app.settings.settings.cloudflare_access_audience",
        "expected-audience",
    )
    signing_key = SimpleNamespace(key="public-key")
    fake_client = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: signing_key
    )
    monkeypatch.setattr(auth, "_get_cloudflare_jwk_client", lambda url: fake_client)

    captured: dict[str, Any] = {}

    def fake_decode(token, key, **kwargs):
        captured.update(token=token, key=key, **kwargs)
        return {"sub": "subject", "email": "admin@example.com"}

    monkeypatch.setattr(auth.jwt, "decode", fake_decode)
    claims = auth._decode_cloudflare_access_token("signed-token")

    assert claims["email"] == "admin@example.com"
    assert captured["algorithms"] == ["RS256"]
    assert captured["audience"] == "expected-audience"
    assert captured["issuer"] == "https://petirlabs.cloudflareaccess.com"
    assert captured["options"]["require"] == [
        "exp",
        "iat",
        "aud",
        "iss",
        "sub",
        "email",
    ]


def test_cloudflare_decoder_verifies_real_rs256_signature_and_expiry(monkeypatch):
    from app.query import auth

    monkeypatch.setattr(
        "app.settings.settings.cloudflare_access_team_domain",
        "team.cloudflareaccess.com",
    )
    monkeypatch.setattr("app.settings.settings.cloudflare_access_audience", "aud-1")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    class FakeJwkClient:
        def get_signing_key_from_jwt(self, token):
            assert token
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(auth, "_get_cloudflare_jwk_client", lambda _: FakeJwkClient())
    now = datetime.now(timezone.utc)

    def encoded(expiry):
        return jwt.encode(
            {
                "sub": "subject-1",
                "email": "admin@example.com",
                "iss": "https://team.cloudflareaccess.com",
                "aud": ["aud-1"],
                "iat": now,
                "exp": expiry,
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    claims = auth._decode_cloudflare_access_token(encoded(now + timedelta(minutes=5)))
    assert claims["email"] == "admin@example.com"

    with pytest.raises(HTTPException) as exc:
        auth._decode_cloudflare_access_token(encoded(now - timedelta(minutes=1)))
    assert exc.value.status_code == 401
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "UNAUTHORIZED"


def test_docs_can_be_disabled_without_breaking_healthcheck(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr("app.settings.settings.api_docs_enabled", False)
    client = TestClient(create_app())

    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
