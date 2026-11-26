from __future__ import annotations

import hashlib
import hmac
import ipaddress
import time
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock

from fastapi import Depends, Header, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.ingest.errors import IngestError
from app.models.registry import EdgeNode
from app.settings import settings


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _trusted_networks(value: str) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    networks = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue
    return tuple(networks)


def _ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def client_identity(request: Request, *, trusted_proxy_cidrs: str) -> str:
    peer = request.client.host if request.client is not None else "unknown"
    peer_ip = _ip(peer)
    trusted = _trusted_networks(trusted_proxy_cidrs)
    if peer_ip is None or not any(peer_ip in network for network in trusted):
        return peer

    cloudflare_ip = _ip(request.headers.get("cf-connecting-ip", ""))
    if cloudflare_ip is not None:
        return str(cloudflare_ip)

    forwarded = request.headers.get("x-forwarded-for", "")
    chain = [address for value in forwarded.split(",") if (address := _ip(value)) is not None]
    if not chain:
        return peer
    for address in reversed(chain):
        if not any(address in network for network in trusted):
            return str(address)
    return str(chain[0])


@dataclass
class _InvalidClientState:
    attempts: deque[float] = field(default_factory=deque)
    blocked_until: float = 0.0


class InvalidBearerLimiter:
    def __init__(
        self,
        *,
        max_failures: int,
        window_seconds: int,
        block_seconds: int,
        max_clients: int,
    ) -> None:
        if min(max_failures, window_seconds, block_seconds, max_clients) <= 0:
            raise ValueError("invalid bearer limiter bounds must be positive")
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._block_seconds = block_seconds
        self._max_clients = max_clients
        self._lock = Lock()
        self._clients: OrderedDict[str, _InvalidClientState] = OrderedDict()

    def _prune(self, state: _InvalidClientState, now: float) -> None:
        cutoff = now - self._window_seconds
        while state.attempts and state.attempts[0] <= cutoff:
            state.attempts.popleft()

    def start_attempt(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            state = self._clients.get(key)
            if state is None:
                while len(self._clients) >= self._max_clients:
                    self._clients.popitem(last=False)
                state = _InvalidClientState()
                self._clients[key] = state
            else:
                self._clients.move_to_end(key)
            self._prune(state, now)
            if state.blocked_until > now:
                return False
            if len(state.attempts) >= self._max_failures:
                state.blocked_until = now + self._block_seconds
                return False
            state.attempts.append(now)
            return True

    def record_success(self, key: str) -> None:
        with self._lock:
            self._clients.pop(key, None)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            state = self._clients.get(key)
            if state is None:
                return True
            self._prune(state, now)
            return state.blocked_until <= now and len(state.attempts) < self._max_failures

    def record_failure(self, key: str) -> None:
        self.start_attempt(key)

    def clear(self) -> None:
        with self._lock:
            self._clients.clear()

    @property
    def tracked_clients(self) -> int:
        with self._lock:
            return len(self._clients)


_invalid_bearer_limiter = InvalidBearerLimiter(
    max_failures=settings.invalid_bearer_max_failures,
    window_seconds=settings.invalid_bearer_window_seconds,
    block_seconds=settings.invalid_bearer_block_seconds,
    max_clients=settings.invalid_bearer_max_clients,
)


def _invalid_bearer_backpressure() -> IngestError:
    return IngestError(429, "BACKPRESSURE", "too many invalid authentication attempts")


def verify_node_token(
    request: Request,
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> EdgeNode:
    identity = client_identity(request, trusted_proxy_cidrs=settings.trusted_proxy_cidrs)
    if not _invalid_bearer_limiter.start_attempt(identity):
        raise _invalid_bearer_backpressure()

    if not authorization:
        raise IngestError(401, "BAD_TOKEN", "missing or malformed bearer token")
    scheme, separator, token = authorization.partition(" ")
    token = token.strip()
    if separator != " " or scheme.lower() != "bearer" or not token or len(token) > 512:
        raise IngestError(401, "BAD_TOKEN", "missing or malformed bearer token")
    candidate = hash_token(token)

    matched: EdgeNode | None = None
    candidates = session.execute(
        select(EdgeNode).where(
            or_(
                EdgeNode.api_token_hash == candidate,
                EdgeNode.previous_token_hash == candidate,
            )
        )
    ).scalars()
    for node in candidates:
        if hmac.compare_digest(node.api_token_hash, candidate):
            matched = node
            break
        if node.previous_token_hash and hmac.compare_digest(
            node.previous_token_hash, candidate
        ):
            matched = node
            break
    if matched is None:
        raise IngestError(401, "BAD_TOKEN", "no node matches the supplied token")
    _invalid_bearer_limiter.record_success(identity)
    if not matched.enabled:
        raise IngestError(403, "NODE_DISABLED", f"node {matched.node_id} is disabled")
    return matched


class _SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self._max = max_requests
        self._window = window_seconds
        self._lock = Lock()
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            bucket = self._buckets[key]
            bucket[:] = [t for t in bucket if t > cutoff]
            if len(bucket) >= self._max:
                return False
            bucket.append(now)
            return True


_ingest_limiter = _SlidingWindowLimiter(
    max_requests=settings.rate_limit_per_node,
    window_seconds=settings.rate_limit_window_seconds,
)


def check_rate_limit(node: EdgeNode) -> None:
    if not _ingest_limiter.allow(node.node_id):
        raise IngestError(
            429, "BACKPRESSURE", f"rate limit exceeded for node {node.node_id}"
        )
