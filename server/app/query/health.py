from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.lightning import LightningMinuteSummary
from app.models.ops import SystemEvent
from app.models.registry import EdgeNode
from app.models.weather import WeatherMinuteSummary
from app.query.auth import verify_dashboard_user
from app.query.freshness import age_seconds, status_for_age
from app.schemas.query import HealthResponse, StreamFreshness

router = APIRouter(prefix="/api/health", tags=["health"], dependencies=[Depends(verify_dashboard_user)])

_STREAMS = [
    ("weather_minute_summary", WeatherMinuteSummary, WeatherMinuteSummary.minute_utc),
    ("lightning_minute_summary", LightningMinuteSummary, LightningMinuteSummary.minute_utc),
    ("system_events", SystemEvent, SystemEvent.ts_pi_utc),
]


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

    streams: list[StreamFreshness] = []
    worst_age: Optional[float] = None
    for name, model, ts_col in _STREAMS:
        stmt = select(func.max(ts_col))
        if node:
            stmt = stmt.where(model.node_id == node)
        last_ts = session.execute(stmt).scalar_one_or_none()
        age = age_seconds(last_ts, now)
        streams.append(
            StreamFreshness(
                table=name,
                last_ts_utc=last_ts.isoformat() if last_ts else None,
                age_seconds=age,
                status=status_for_age(age),
            )
        )
        if age is not None:
            worst_age = age if worst_age is None else max(worst_age, age)

    last_seen = node_row.last_seen_utc if node_row else None
    sync_lag = age_seconds(last_seen, now)
    node_status = status_for_age(sync_lag) if node_row else "no_data"

    return HealthResponse(
        node_id=node_row.node_id if node_row else node,
        node_status=node_status,
        last_seen_utc=last_seen.isoformat() if last_seen else None,
        sync_lag_seconds=sync_lag,
        streams=streams,
    )
