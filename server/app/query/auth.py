from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from app.settings import settings


def verify_dashboard_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    if not settings.dashboard_auth_enabled:
        return None
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "missing X-API-Key header"},
        )
    if not hmac.compare_digest(x_api_key, settings.dashboard_api_key):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "invalid API key"},
        )
    return x_api_key
