from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class HistoryMeta(BaseModel):
    count: int
    downsampled: bool


class HistoryResponse(BaseModel):
    node_id: Optional[str]
    interval: str
    from_utc: str
    to_utc: str
    series: list[dict[str, Any]]
    meta: HistoryMeta


class LatestResponse(BaseModel):
    node_id: Optional[str]
    minute: Optional[dict[str, Any]]


class StreamFreshness(BaseModel):
    table: str
    kind: str
    last_ts_utc: Optional[str]
    age_seconds: Optional[float]
    status: str


class HealthResponse(BaseModel):
    node_id: Optional[str]
    node_status: str
    last_seen_utc: Optional[str]
    sync_lag_seconds: Optional[float]
    streams: list[StreamFreshness]
