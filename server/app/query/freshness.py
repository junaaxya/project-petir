from __future__ import annotations

from datetime import datetime, timezone

FRESH_FACTOR = 2
STALE_FACTOR = 5
DEFAULT_SEND_INTERVAL_S = 15


def status_for_age(age_seconds: float | None, send_interval_s: int = DEFAULT_SEND_INTERVAL_S) -> str:
    if age_seconds is None:
        return "no_data"
    if age_seconds < FRESH_FACTOR * send_interval_s:
        return "fresh"
    if age_seconds < STALE_FACTOR * send_interval_s:
        return "stale"
    return "offline"


def age_seconds(last_ts: datetime | None, now: datetime | None = None) -> float | None:
    if last_ts is None:
        return None
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)
    ref = now or datetime.now(timezone.utc)
    return max(0.0, (ref - last_ts).total_seconds())
