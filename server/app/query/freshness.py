from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

FRESH_FACTOR = 2
STALE_FACTOR = 5
DEFAULT_SEND_INTERVAL_S = 15
NODE_FRESH_SECONDS = 60
NODE_STALE_SECONDS = 180

NodeStatus = Literal["fresh", "stale", "offline", "no_data"]
StreamKind = Literal["cadence", "event"]
StreamStatus = Literal["fresh", "stale", "offline", "no_data", "idle", "unknown"]


@dataclass(frozen=True)
class StreamFreshnessPolicy:
    kind: StreamKind
    interval_s: int | None = None


STREAM_FRESHNESS_POLICIES: dict[str, StreamFreshnessPolicy] = {
    "weather_minute_summary": StreamFreshnessPolicy(kind="cadence", interval_s=60),
    "lightning_minute_summary": StreamFreshnessPolicy(kind="event"),
    "system_events": StreamFreshnessPolicy(kind="event"),
}


def status_for_age(
    age_seconds: float | None,
    send_interval_s: int = DEFAULT_SEND_INTERVAL_S,
) -> NodeStatus:
    if age_seconds is None:
        return "no_data"
    if age_seconds < FRESH_FACTOR * send_interval_s:
        return "fresh"
    if age_seconds < STALE_FACTOR * send_interval_s:
        return "stale"
    return "offline"


def status_for_thresholds(
    age_seconds: float | None,
    fresh_seconds: int,
    stale_seconds: int,
) -> NodeStatus:
    if age_seconds is None:
        return "no_data"
    if age_seconds < fresh_seconds:
        return "fresh"
    if age_seconds < stale_seconds:
        return "stale"
    return "offline"


def status_for_node(age_seconds: float | None) -> NodeStatus:
    return status_for_thresholds(age_seconds, NODE_FRESH_SECONDS, NODE_STALE_SECONDS)


def status_for_event(age_seconds: float | None, node_status: NodeStatus) -> StreamStatus:
    if age_seconds is None:
        return "no_data"
    if node_status == "offline":
        return "unknown"
    return "idle"


def age_seconds(last_ts: datetime | None, now: datetime | None = None) -> float | None:
    if last_ts is None:
        return None
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)
    ref = now or datetime.now(timezone.utc)
    return max(0.0, (ref - last_ts).total_seconds())
