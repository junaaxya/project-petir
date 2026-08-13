from __future__ import annotations

import math
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.ops import SystemEvent
from app.query.auth import verify_dashboard_user
from app.query.downsample import parse_range

router = APIRouter(prefix="/api/system", tags=["system"], dependencies=[Depends(verify_dashboard_user)])

ROUTINE_EVENT_TYPES = {"ingest_heartbeat"}
IMPORTANT_INFO_EVENT_TYPES = {"node_online", "node_offline"}
TECHNICAL_ISSUE_EXCLUDED_SOURCES = {"siren_audit_client"}
ACTIVITY_EXCLUDED_EVENT_TYPES = {"siren_audit_poll_empty"}
SystemEventScope = Literal["all", "important", "status_changes", "technical_issues"]
SystemEventGroup = Literal["all", "heartbeat", "status", "other"]


def _event_to_dict(row: SystemEvent) -> dict[str, Any]:
    return {
        "edge_id": row.edge_id,
        "ts_pi_utc": row.ts_pi_utc.isoformat() if row.ts_pi_utc else None,
        "source": row.source,
        "level": row.level,
        "event_type": row.event_type,
        "message": row.message,
    }


def _apply_scope(stmt, scope: SystemEventScope):
    if scope == "important":
        return stmt.where(
            (~SystemEvent.event_type.in_(ROUTINE_EVENT_TYPES))
            & (
                SystemEvent.level.in_(["warn", "error", "critical"])
                | SystemEvent.event_type.in_(IMPORTANT_INFO_EVENT_TYPES)
            )
        )
    if scope == "status_changes":
        return stmt.where(SystemEvent.event_type.in_(IMPORTANT_INFO_EVENT_TYPES))
    if scope == "technical_issues":
        return stmt.where(
            (~SystemEvent.event_type.in_(ROUTINE_EVENT_TYPES))
            & (~SystemEvent.event_type.in_(IMPORTANT_INFO_EVENT_TYPES))
            & (~SystemEvent.source.in_(TECHNICAL_ISSUE_EXCLUDED_SOURCES))
            & SystemEvent.level.in_(["warn", "error", "critical"])
        )
    return stmt


def _apply_event_group(stmt, event_group: SystemEventGroup):
    if event_group == "heartbeat":
        return stmt.where(SystemEvent.event_type.in_(ROUTINE_EVENT_TYPES))
    if event_group == "status":
        return stmt.where(SystemEvent.event_type.in_(IMPORTANT_INFO_EVENT_TYPES))
    if event_group == "other":
        return stmt.where(
            (~SystemEvent.event_type.in_(ROUTINE_EVENT_TYPES))
            & (~SystemEvent.event_type.in_(IMPORTANT_INFO_EVENT_TYPES))
            & (~SystemEvent.event_type.in_(ACTIVITY_EXCLUDED_EVENT_TYPES))
        )
    return stmt


@router.get("/events")
def system_events(
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    important_only: bool = Query(default=False),
    scope: SystemEventScope = Query(default="all"),
    event_group: SystemEventGroup = Query(default="all"),
    limit: int = Query(default=200, ge=1, le=1000),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    from_dt, to_dt = parse_range(from_, to, "raw")
    count_stmt = (
        select(func.count())
        .select_from(SystemEvent)
        .where(SystemEvent.ts_pi_utc >= from_dt)
        .where(SystemEvent.ts_pi_utc < to_dt)
    )
    if node:
        count_stmt = count_stmt.where(SystemEvent.node_id == node)
    if level:
        count_stmt = count_stmt.where(SystemEvent.level == level)

    effective_scope: SystemEventScope = "important" if important_only and scope == "all" else scope
    count_stmt = _apply_scope(count_stmt, effective_scope)
    count_stmt = _apply_event_group(count_stmt, event_group)
    total_items = int(session.execute(count_stmt).scalar() or 0)
    total_pages = max(1, math.ceil(total_items / page_size))
    current_page = min(page, total_pages)
    offset = (current_page - 1) * page_size

    stmt = (
        select(SystemEvent)
        .where(SystemEvent.ts_pi_utc >= from_dt)
        .where(SystemEvent.ts_pi_utc < to_dt)
        .order_by(SystemEvent.ts_pi_utc.desc())
        .limit(page_size)
        .offset(offset)
    )
    if node:
        stmt = stmt.where(SystemEvent.node_id == node)
    if level:
        stmt = stmt.where(SystemEvent.level == level)
    stmt = _apply_scope(stmt, effective_scope)
    stmt = _apply_event_group(stmt, event_group)

    items = []
    for row in session.execute(stmt).scalars():
        items.append(_event_to_dict(row))
    return {
        "node_id": node,
        "items": items,
        "meta": {
            "count": len(items),
            "scope": effective_scope,
            "event_group": event_group,
            "page": current_page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_prev": current_page > 1,
            "has_next": current_page < total_pages,
            "requested_limit": limit,
        },
    }


@router.get("/summary")
def system_summary(
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    important_only: bool = Query(default=False),
    scope: SystemEventScope = Query(default="all"),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    from_dt, to_dt = parse_range(from_, to, "raw")
    effective_scope: SystemEventScope = "important" if important_only and scope == "all" else scope

    base = (
        select(SystemEvent.level, func.count().label("count"))
        .where(SystemEvent.ts_pi_utc >= from_dt)
        .where(SystemEvent.ts_pi_utc < to_dt)
        .group_by(SystemEvent.level)
    )
    if node:
        base = base.where(SystemEvent.node_id == node)
    base = _apply_scope(base, effective_scope)
    rows = session.execute(base).all()
    counts = {r[0] or "unknown": r[1] for r in rows}
    total = sum(counts.values())

    recent_stmt = (
        select(SystemEvent)
        .where(SystemEvent.ts_pi_utc >= from_dt)
        .where(SystemEvent.ts_pi_utc < to_dt)
        .order_by(SystemEvent.ts_pi_utc.desc())
        .limit(10)
    )
    if node:
        recent_stmt = recent_stmt.where(SystemEvent.node_id == node)
    recent_stmt = _apply_scope(recent_stmt, effective_scope)
    recent = [_event_to_dict(r) for r in session.execute(recent_stmt).scalars()]

    return {
        "node_id": node,
        "from_utc": from_dt.isoformat(),
        "to_utc": to_dt.isoformat(),
        "total_events": total,
        "counts_by_level": counts,
        "recent": recent,
        "scope": effective_scope,
    }
