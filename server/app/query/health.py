from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.lightning import LightningMinuteSummary
from app.models.ops import SystemEvent
from app.models.registry import EdgeNode
from app.models.weather import WeatherMinuteSummary
from app.query.auth import verify_dashboard_user
from app.query.freshness import (
    NodeStatus,
    STREAM_FRESHNESS_POLICIES,
    StreamFreshnessPolicy,
    age_seconds,
    status_for_age,
    status_for_event,
    status_for_node,
)
from app.schemas.query import (
    HealthResponse,
    StreamFreshness,
    WanFailoverChecks,
    WanFailoverDecision,
    WanFailoverEvent,
    WanFailoverFrontendSummary,
    WanFailoverHealthCheck,
    WanFailoverRoute,
    WanFailoverStatus,
)
from app.settings import settings

router = APIRouter(prefix="/api/health", tags=["health"], dependencies=[Depends(verify_dashboard_user)])

_STREAMS = [
    (
        "weather_minute_summary",
        WeatherMinuteSummary,
        WeatherMinuteSummary.minute_utc,
        STREAM_FRESHNESS_POLICIES["weather_minute_summary"],
    ),
    (
        "lightning_minute_summary",
        LightningMinuteSummary,
        LightningMinuteSummary.minute_utc,
        STREAM_FRESHNESS_POLICIES["lightning_minute_summary"],
    ),
    (
        "system_events",
        SystemEvent,
        SystemEvent.ts_pi_utc,
        STREAM_FRESHNESS_POLICIES["system_events"],
    ),
]


def _stream_status(
    age: float | None,
    policy: StreamFreshnessPolicy,
    node_status: NodeStatus,
) -> str:
    if policy.kind == "cadence":
        if policy.interval_s is None:
            raise ValueError("cadence stream policy requires interval_s")
        return status_for_age(age, send_interval_s=policy.interval_s)
    return status_for_event(age, node_status)


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _snapshot_dir_for_node(node_id: Optional[str]) -> Path | None:
    base = (settings.wan_failover_snapshot_dir or "").strip()
    if not base or not node_id:
        return None
    return Path(base) / node_id


def _load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _coerce_check(raw: Any) -> WanFailoverHealthCheck:
    raw = raw if isinstance(raw, dict) else {}
    return WanFailoverHealthCheck(
        iface=_safe_str(raw.get("iface")),
        connection=_safe_str(raw.get("connection")),
        ipv4=_safe_str(raw.get("ipv4")),
        gateway=_safe_str(raw.get("gateway")),
        ok=_safe_bool(raw.get("ok")),
        detail=_safe_str(raw.get("detail")),
        route_metric=_safe_int(raw.get("route_metric")),
    )


def _coerce_routes(raw: Any) -> list[WanFailoverRoute]:
    if not isinstance(raw, list):
        return []
    items: list[WanFailoverRoute] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        items.append(
            WanFailoverRoute(
                iface=_safe_str(item.get("iface")),
                gateway=_safe_str(item.get("gateway")),
                metric=_safe_int(item.get("metric")),
                kind=_safe_str(item.get("kind")),
                raw=_safe_str(item.get("raw")),
            )
        )
    return items


def _coerce_events(raw: Any) -> list[WanFailoverEvent]:
    if not isinstance(raw, list):
        return []
    items: list[WanFailoverEvent] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        details = item.get("details")
        items.append(
            WanFailoverEvent(
                ts_utc=_safe_str(item.get("ts_utc")),
                event_type=_safe_str(item.get("event_type")),
                active_uplink_iface=_safe_str(item.get("active_uplink_iface")),
                active_uplink_kind=_safe_str(item.get("active_uplink_kind")),
                message=_safe_str(item.get("message")),
                details=details if isinstance(details, dict) else None,
            )
        )
    return items


def _resolve_primary_badge(active_kind: str | None, summary_badge: str | None) -> str:
    normalized = (summary_badge or "").strip().lower()
    if normalized in {"ethernet-primary", "wifi-fallback", "unknown"}:
        return normalized
    if active_kind == "ethernet":
        return "ethernet-primary"
    if active_kind == "wifi":
        return "wifi-fallback"
    return "unknown"


def _load_wan_failover(node_id: Optional[str]) -> WanFailoverStatus:
    fallback = WanFailoverStatus(
        available=False,
        primary_badge="unknown",
        message="WAN failover status belum tersedia",
        decision=WanFailoverDecision(),
        checks=WanFailoverChecks(eth=WanFailoverHealthCheck(), wifi=WanFailoverHealthCheck()),
        frontend_summary=WanFailoverFrontendSummary(
            badge="unknown",
            message="WAN failover status belum tersedia",
            recommended_color="gray",
        ),
        recent_events=[],
        default_routes=[],
    )

    snapshot_dir = _snapshot_dir_for_node(node_id)
    if snapshot_dir is None:
        return fallback

    status_raw = _load_json(snapshot_dir / "wan_failover_status.json")
    events_raw = _load_json(snapshot_dir / "wan_failover_events_recent.json")
    if not isinstance(status_raw, dict):
        return fallback

    decision_candidate = status_raw.get("decision")
    decision_raw: dict[str, Any] = decision_candidate if isinstance(decision_candidate, dict) else {}
    checks_candidate = status_raw.get("checks")
    checks_raw: dict[str, Any] = checks_candidate if isinstance(checks_candidate, dict) else {}
    summary_candidate = status_raw.get("frontend_summary")
    summary_raw: dict[str, Any] = summary_candidate if isinstance(summary_candidate, dict) else {}
    active_kind = _safe_str(status_raw.get("active_uplink_kind"))
    primary_badge = _resolve_primary_badge(active_kind, _safe_str(summary_raw.get("badge")))
    message = _safe_str(summary_raw.get("message")) or "WAN failover status tersedia"

    return WanFailoverStatus(
        available=True,
        ts_utc=_safe_str(status_raw.get("ts_utc")),
        mode=_safe_str(status_raw.get("mode")),
        active_uplink_iface=_safe_str(status_raw.get("active_uplink_iface")),
        active_uplink_kind=active_kind,
        primary_badge=primary_badge,
        message=message,
        decision=WanFailoverDecision(
            eth_fail_count=_safe_int(decision_raw.get("eth_fail_count")),
            eth_recover_count=_safe_int(decision_raw.get("eth_recover_count")),
            fail_threshold=_safe_int(decision_raw.get("fail_threshold")),
            recover_threshold=_safe_int(decision_raw.get("recover_threshold")),
            last_change=_safe_str(decision_raw.get("last_change")),
            last_event=_safe_str(decision_raw.get("last_event")),
        ),
        checks=WanFailoverChecks(
            eth=_coerce_check(checks_raw.get("eth")),
            wifi=_coerce_check(checks_raw.get("wifi")),
        ),
        default_routes=_coerce_routes(status_raw.get("default_routes")),
        frontend_summary=WanFailoverFrontendSummary(
            badge=primary_badge,
            message=message,
            recommended_color=_safe_str(summary_raw.get("recommended_color")),
        ),
        recent_events=_coerce_events(events_raw),
    )


@router.get("/latest", response_model=HealthResponse)
def health_latest(
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> HealthResponse:
    now = datetime.now(timezone.utc)

    node_row: Optional[EdgeNode] = None
    if node:
        node_row = session.get(EdgeNode, node)
    else:
        node_row = session.execute(
            select(EdgeNode).order_by(EdgeNode.last_seen_utc.desc().nullslast()).limit(1)
        ).scalars().first()

    last_seen = node_row.last_seen_utc if node_row else None
    sync_lag = age_seconds(last_seen, now)
    node_status = status_for_node(sync_lag) if node_row else "no_data"

    streams: list[StreamFreshness] = []
    for name, model, ts_col, policy in _STREAMS:
        stmt = select(func.max(ts_col))
        if node:
            stmt = stmt.where(model.node_id == node)
        last_ts = session.execute(stmt).scalar_one_or_none()
        age = age_seconds(last_ts, now)
        streams.append(
            StreamFreshness(
                table=name,
                kind=policy.kind,
                last_ts_utc=last_ts.isoformat() if last_ts else None,
                age_seconds=age,
                status=_stream_status(age, policy, node_status),
            )
        )

    effective_node_id = node_row.node_id if node_row else node
    return HealthResponse(
        node_id=effective_node_id,
        node_status=node_status,
        last_seen_utc=last_seen.isoformat() if last_seen else None,
        sync_lag_seconds=sync_lag,
        streams=streams,
        wan_failover=_load_wan_failover(effective_node_id),
    )
