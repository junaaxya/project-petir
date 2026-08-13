from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ops import SystemEvent
from app.models.registry import EdgeNode
from app.query.freshness import age_seconds, status_for_node
from app.settings import settings

SERVER_MONITOR_SOURCE = "server-monitor"
EVENT_NODE_OFFLINE = "node_offline"
EVENT_NODE_ONLINE = "node_online"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _server_event_epoch() -> uuid.UUID:
    return uuid.UUID(settings.availability_server_event_epoch)


def _next_server_edge_id(session: Session) -> int:
    value = session.execute(
        select(func.max(SystemEvent.edge_id)).where(SystemEvent.source == SERVER_MONITOR_SOURCE)
    ).scalar_one()
    return int(value or 0) + 1


def _current_status(last_seen_utc: datetime | None, now: datetime) -> str:
    return status_for_node(age_seconds(last_seen_utc, now))


def _offline_message() -> str:
    return "Sensor cuaca offline: tidak ada data baru dari Raspberry Pi."


def _online_message() -> str:
    return "Sensor cuaca online kembali: data dari Raspberry Pi kembali diterima."


def _build_event(
    *,
    session: Session,
    node: EdgeNode,
    now: datetime,
    previous_status: str,
    current_status: str,
    event_type: str,
) -> SystemEvent:
    age = age_seconds(node.last_seen_utc, now)
    message = _offline_message() if event_type == EVENT_NODE_OFFLINE else _online_message()
    level = "warn" if event_type == EVENT_NODE_OFFLINE else "info"
    return SystemEvent(
        node_id=node.node_id,
        db_epoch=_server_event_epoch(),
        ingest_run_id=None,
        edge_id=_next_server_edge_id(session),
        ts_pi_utc=now,
        source=SERVER_MONITOR_SOURCE,
        level=level,
        event_type=event_type,
        message=message,
        details_json={
            "origin": "server",
            "previous_status": previous_status,
            "current_status": current_status,
            "detected_at_utc": now.isoformat(),
            "last_seen_utc": node.last_seen_utc.isoformat() if node.last_seen_utc else None,
            "age_seconds": age,
            "reason": "last_seen_timeout"
            if event_type == EVENT_NODE_OFFLINE
            else "data_resumed",
        },
        created_at_utc=now,
    )


def run_availability_check(
    session: Session,
    now: datetime | None = None,
) -> dict[str, Any]:
    ref = now or _now()
    nodes = session.execute(
        select(EdgeNode).where(EdgeNode.enabled.is_(True)).order_by(EdgeNode.node_id)
    ).scalars().all()

    transitions: list[dict[str, Any]] = []
    events_created = 0

    for node in nodes:
        current_status = _current_status(node.last_seen_utc, ref)
        previous_status = node.availability_status

        if previous_status is None:
            node.availability_status = current_status
            node.availability_changed_at_utc = ref
            continue

        event_type: str | None = None
        if previous_status != "offline" and current_status == "offline":
            event_type = EVENT_NODE_OFFLINE
        elif (
            previous_status == "offline"
            and current_status == settings.availability_recovery_status
        ):
            event_type = EVENT_NODE_ONLINE

        if previous_status != current_status:
            node.availability_status = current_status
            node.availability_changed_at_utc = ref

        if event_type is None:
            continue

        session.add(
            _build_event(
                session=session,
                node=node,
                now=ref,
                previous_status=previous_status,
                current_status=current_status,
                event_type=event_type,
            )
        )
        node.availability_last_event_type = event_type
        node.availability_last_event_at_utc = ref
        events_created += 1
        transitions.append(
            {
                "node_id": node.node_id,
                "previous_status": previous_status,
                "current_status": current_status,
                "event_type": event_type,
            }
        )

    session.commit()
    return {
        "checked_at_utc": ref.isoformat(),
        "nodes_checked": len(nodes),
        "events_created": events_created,
        "transitions": transitions,
    }