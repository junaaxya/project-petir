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


class WanFailoverHealthCheck(BaseModel):
    iface: Optional[str] = None
    connection: Optional[str] = None
    ipv4: Optional[str] = None
    gateway: Optional[str] = None
    ok: Optional[bool] = None
    detail: Optional[str] = None
    route_metric: Optional[int] = None


class WanFailoverDecision(BaseModel):
    eth_fail_count: Optional[int] = None
    eth_recover_count: Optional[int] = None
    fail_threshold: Optional[int] = None
    recover_threshold: Optional[int] = None
    last_change: Optional[str] = None
    last_event: Optional[str] = None


class WanFailoverChecks(BaseModel):
    eth: WanFailoverHealthCheck
    wifi: WanFailoverHealthCheck


class WanFailoverRoute(BaseModel):
    iface: Optional[str] = None
    gateway: Optional[str] = None
    metric: Optional[int] = None
    kind: Optional[str] = None
    raw: Optional[str] = None


class WanFailoverFrontendSummary(BaseModel):
    badge: Optional[str] = None
    message: Optional[str] = None
    recommended_color: Optional[str] = None


class WanFailoverEvent(BaseModel):
    ts_utc: Optional[str] = None
    event_type: Optional[str] = None
    active_uplink_iface: Optional[str] = None
    active_uplink_kind: Optional[str] = None
    message: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class WanFailoverStatus(BaseModel):
    available: bool = False
    ts_utc: Optional[str] = None
    mode: Optional[str] = None
    active_uplink_iface: Optional[str] = None
    active_uplink_kind: Optional[str] = None
    primary_badge: str = "unknown"
    message: str = "WAN failover status belum tersedia"
    decision: WanFailoverDecision
    checks: WanFailoverChecks
    default_routes: list[WanFailoverRoute] = []
    frontend_summary: WanFailoverFrontendSummary
    recent_events: list[WanFailoverEvent] = []


class HealthResponse(BaseModel):
    node_id: Optional[str]
    node_status: str
    last_seen_utc: Optional[str]
    sync_lag_seconds: Optional[float]
    streams: list[StreamFreshness]
    wan_failover: Optional[WanFailoverStatus] = None


class ForecastLatestItem(BaseModel):
    forecast_type: str
    computed_at_utc: str
    source_window_start_utc: Optional[str] = None
    source_window_end_utc: Optional[str] = None
    target_time_utc: Optional[str] = None
    horizon_minutes: Optional[int] = None
    score: Optional[float] = None
    value_numeric: Optional[float] = None
    label: Optional[str] = None
    confidence: Optional[float] = None
    status: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class ForecastLatestResponse(BaseModel):
    node_id: Optional[str]
    computed_at_utc: Optional[str]
    items: list[ForecastLatestItem]
