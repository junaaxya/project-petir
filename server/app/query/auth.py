from __future__ import annotations

import hmac
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from app.settings import settings

AccessRole = Literal["operator", "admin"]


@dataclass(frozen=True)
class AccessPrincipal:
    subject: str
    role: AccessRole
    auth_method: Literal["api_key", "cloudflare_access", "legacy_dashboard"]


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _csv_identities(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def verify_dashboard_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    """Preserve the existing Petir 1 public/API-key dashboard behavior."""
    if not settings.dashboard_auth_enabled:
        return None
    if not x_api_key:
        raise _error(401, "UNAUTHORIZED", "missing X-API-Key header")
    if not settings.dashboard_api_key or not hmac.compare_digest(
        x_api_key, settings.dashboard_api_key
    ):
        raise _error(401, "UNAUTHORIZED", "invalid API key")
    return x_api_key


@lru_cache(maxsize=8)
def _get_cloudflare_jwk_client(certs_url: str) -> PyJWKClient:
    return PyJWKClient(certs_url, cache_keys=True, lifespan=300)


def _cloudflare_issuer() -> str:
    domain = settings.cloudflare_access_team_domain.strip().lower()
    domain = domain.removeprefix("https://").rstrip("/")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.cloudflareaccess\.com", domain):
        raise _error(
            503,
            "ACCESS_CONTROL_CONFIG_INVALID",
            "Cloudflare Access team domain is not configured correctly",
        )
    return f"https://{domain}"


def _decode_cloudflare_access_token(token: str) -> dict[str, Any]:
    issuer = _cloudflare_issuer()
    audience = settings.cloudflare_access_audience.strip()
    if not audience:
        raise _error(
            503,
            "ACCESS_CONTROL_CONFIG_INVALID",
            "Cloudflare Access audience is not configured",
        )
    certs_url = f"{issuer}/cdn-cgi/access/certs"
    try:
        signing_key = _get_cloudflare_jwk_client(certs_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "aud", "iss", "sub", "email"]},
        )
    except HTTPException:
        raise
    except (jwt.PyJWTError, ValueError, OSError) as exc:
        raise _error(401, "UNAUTHORIZED", "invalid Cloudflare Access token") from exc
    if not isinstance(claims, dict):
        raise _error(401, "UNAUTHORIZED", "invalid Cloudflare Access token")
    return claims


def _api_key_principal(x_api_key: str | None) -> AccessPrincipal:
    admin_key = settings.admin_api_key
    operator_key = settings.operator_api_key
    configured = bool(admin_key or operator_key)
    if not configured:
        raise _error(
            503,
            "ACCESS_CONTROL_CONFIG_INVALID",
            "API-key access control is enabled without a configured key",
        )
    if admin_key and operator_key and hmac.compare_digest(admin_key, operator_key):
        raise _error(
            503,
            "ACCESS_CONTROL_CONFIG_INVALID",
            "admin and operator API keys must be different",
        )
    if not x_api_key:
        raise _error(401, "UNAUTHORIZED", "missing X-API-Key header")
    if admin_key and hmac.compare_digest(x_api_key, admin_key):
        return AccessPrincipal("api-key-admin", "admin", "api_key")
    if operator_key and hmac.compare_digest(x_api_key, operator_key):
        return AccessPrincipal("api-key-operator", "operator", "api_key")
    raise _error(401, "UNAUTHORIZED", "invalid API key")


def _cloudflare_principal(token: str | None) -> AccessPrincipal:
    if not token:
        raise _error(401, "UNAUTHORIZED", "missing Cloudflare Access JWT")
    claims = _decode_cloudflare_access_token(token)
    email = str(claims.get("email", "")).strip().lower()
    if not email:
        raise _error(401, "UNAUTHORIZED", "Cloudflare Access token has no email identity")
    admin_emails = _csv_identities(settings.cloudflare_access_admin_emails)
    operator_emails = _csv_identities(settings.cloudflare_access_operator_emails)
    if not admin_emails and not operator_emails:
        raise _error(
            503,
            "ACCESS_CONTROL_CONFIG_INVALID",
            "Cloudflare Access identity allowlists are empty",
        )
    if admin_emails & operator_emails:
        raise _error(
            503,
            "ACCESS_CONTROL_CONFIG_INVALID",
            "Cloudflare Access admin and operator allowlists must not overlap",
        )
    if email in admin_emails:
        return AccessPrincipal(email, "admin", "cloudflare_access")
    if email in operator_emails:
        return AccessPrincipal(email, "operator", "cloudflare_access")
    raise _error(403, "FORBIDDEN", "identity is not authorized for operator access")


def _access_principal(
    *,
    x_api_key: str | None,
    cf_access_jwt_assertion: str | None,
) -> AccessPrincipal:
    mode = settings.admin_auth_mode
    if mode == "disabled":
        raise _error(
            503,
            "ACCESS_CONTROL_NOT_CONFIGURED",
            "privileged API access is disabled until server-side authentication is configured",
        )
    if mode == "api_key":
        return _api_key_principal(x_api_key)
    if mode == "cloudflare_access":
        return _cloudflare_principal(cf_access_jwt_assertion)
    if mode == "legacy_dashboard":
        verify_dashboard_user(x_api_key)
        return AccessPrincipal(
            "legacy-dashboard-user", "admin", "legacy_dashboard"
        )
    raise _error(503, "ACCESS_CONTROL_CONFIG_INVALID", "unsupported access-control mode")


def verify_operator_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    cf_access_jwt_assertion: str | None = Header(
        default=None, alias="Cf-Access-Jwt-Assertion"
    ),
) -> AccessPrincipal:
    return _access_principal(
        x_api_key=x_api_key,
        cf_access_jwt_assertion=cf_access_jwt_assertion,
    )


def verify_admin_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    cf_access_jwt_assertion: str | None = Header(
        default=None, alias="Cf-Access-Jwt-Assertion"
    ),
) -> AccessPrincipal:
    principal = _access_principal(
        x_api_key=x_api_key,
        cf_access_jwt_assertion=cf_access_jwt_assertion,
    )
    if principal.role != "admin":
        raise _error(403, "FORBIDDEN", "admin role required")
    return principal


def require_siren_enabled() -> None:
    if not settings.siren_audit_enabled:
        raise _error(404, "SIREN_DISABLED", "siren audit routes are disabled")
