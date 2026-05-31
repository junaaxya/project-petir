from __future__ import annotations

import hashlib
import hmac
import time
from collections import defaultdict
from threading import Lock

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.ingest.errors import IngestError
from app.models.registry import EdgeNode
from app.settings import settings


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_node_token(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> EdgeNode:
    if not authorization or not authorization.startswith("Bearer "):
        raise IngestError(401, "BAD_TOKEN", "missing or malformed bearer token")
    token = authorization[len("Bearer ") :].strip()
    candidate = hash_token(token)

    matched: EdgeNode | None = None
    for node in session.execute(select(EdgeNode)).scalars():
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
