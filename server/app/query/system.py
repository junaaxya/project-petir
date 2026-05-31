from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.ops import SystemEvent
from app.query.auth import verify_dashboard_user
from app.query.downsample import parse_range

router = APIRouter(prefix="/api/system", tags=["system"], dependencies=[Depends(verify_dashboard_user)])


def _event_to_dict(row: SystemEvent) -> dict[str, Any]:
    return {
        "edge_id": row.edge_id,
        "ts_pi_utc": row.ts_pi_utc.isoformat() if row.ts_pi_utc else None,
        "source": row.source,
        "level": row.level,
        "event_type": row.event_type,
        "message": row.message,
    }


@router.get("/events")
def system_events(
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    from_dt, to_dt = parse_range(from_, to, "raw")
    stmt = (
        select(SystemEvent)
        .where(SystemEvent.ts_pi_utc >= from_dt)
        .where(SystemEvent.ts_pi_utc < to_dt)
        .order_by(SystemEvent.ts_pi_utc.desc())
        .limit(limit)
    )
    if node:
        stmt = stmt.where(SystemEvent.node_id == node)
    if level:
        stmt = stmt.where(SystemEvent.level == level)
    items = []
    for row in session.execute(stmt).scalars():
        items.append(_event_to_dict(row))
    return {"node_id": node, "items": items, "meta": {"count": len(items)}}


@router.get("/summary")
def system_summary(
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    from_dt, to_dt = parse_range(from_, to, "raw")
    base = (
        select(SystemEvent.level, func.count().label("count"))
        .where(SystemEvent.ts_pi_utc >= from_dt)
        .where(SystemEvent.ts_pi_utc < to_dt)
        .group_by(SystemEvent.level)
    )
    if node:
        base = base.where(SystemEvent.node_id == node)
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
    recent = [_event_to_dict(r) for r in session.execute(recent_stmt).scalars()]

    return {
        "node_id": node,
        "from_utc": from_dt.isoformat(),
        "to_utc": to_dt.isoformat(),
        "total_events": total,
        "counts_by_level": counts,
        "recent": recent,
    }
