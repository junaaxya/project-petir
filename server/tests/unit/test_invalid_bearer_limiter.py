from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.ingest.auth import InvalidBearerLimiter, client_identity, verify_node_token
from app.ingest.errors import IngestError


def _request(peer: str, headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/ingest/sync-batch",
            "headers": headers,
            "client": (peer, 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )


def test_untrusted_peer_cannot_spoof_forwarded_client():
    request = _request(
        "198.51.100.20",
        [(b"x-forwarded-for", b"203.0.113.9"), (b"cf-connecting-ip", b"203.0.113.10")],
    )
    assert client_identity(request, trusted_proxy_cidrs="10.0.0.0/8") == "198.51.100.20"


def test_trusted_proxy_uses_original_client_instead_of_collapsing_clients():
    first = _request("10.0.0.2", [(b"x-forwarded-for", b"203.0.113.9, 10.0.0.3")])
    second = _request("10.0.0.2", [(b"cf-connecting-ip", b"203.0.113.10")])
    assert client_identity(first, trusted_proxy_cidrs="10.0.0.0/8") == "203.0.113.9"
    assert client_identity(second, trusted_proxy_cidrs="10.0.0.0/8") == "203.0.113.10"


def test_invalid_bearer_limiter_is_bounded_and_blocks_after_failures():
    limiter = InvalidBearerLimiter(max_failures=2, window_seconds=60, block_seconds=60, max_clients=2)
    assert limiter.is_allowed("client-a")
    limiter.record_failure("client-a")
    assert limiter.is_allowed("client-a")
    limiter.record_failure("client-a")
    assert not limiter.is_allowed("client-a")
    limiter.record_failure("client-b")
    limiter.record_failure("client-c")
    assert limiter.tracked_clients <= 2


def test_invalid_bearer_limiter_is_concurrency_safe():
    limiter = InvalidBearerLimiter(max_failures=10, window_seconds=60, block_seconds=60, max_clients=4)

    with ThreadPoolExecutor(max_workers=16) as pool:
        allowed = list(pool.map(lambda _: limiter.start_attempt("one-client"), range(64)))

    assert sum(allowed) == 10
    assert limiter.tracked_clients == 1


def test_backpressure_happens_before_another_database_lookup(monkeypatch):
    from app.ingest import auth

    limiter = InvalidBearerLimiter(max_failures=2, window_seconds=60, block_seconds=60, max_clients=4)
    monkeypatch.setattr(auth, "_invalid_bearer_limiter", limiter)
    monkeypatch.setattr(auth.settings, "trusted_proxy_cidrs", "")

    request = _request("198.51.100.20", [])
    session = MagicMock(spec=Session)
    session.execute.return_value.scalars.return_value = []

    for _ in range(2):
        with pytest.raises(IngestError) as exc:
            verify_node_token(request, "Bearer definitely-invalid", session)
        assert exc.value.status_code == 401

    with pytest.raises(IngestError) as exc:
        verify_node_token(request, "Bearer another-invalid-token", session)
    assert exc.value.status_code == 429
    assert session.execute.call_count == 2