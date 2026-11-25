from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.forecast import ForecastResult
from app.models.registry import EdgeNode
from app.query.auth import verify_dashboard_user
from app.schemas.query import ForecastLatestItem, ForecastLatestResponse
from app.settings import settings

router = APIRouter(
    prefix="/api/forecast",
    tags=["forecast"],
    dependencies=[Depends(verify_dashboard_user)],
)


def _forecast_to_response(row: ForecastResult) -> ForecastLatestItem:
    legacy = settings.public_data_mode == "legacy_full"
    return ForecastLatestItem(
        forecast_type=row.forecast_type,
        computed_at_utc=row.computed_at_utc.isoformat(),
        source_window_start_utc=_iso(row.source_window_start_utc),
        source_window_end_utc=_iso(row.source_window_end_utc),
        target_time_utc=_iso(row.target_time_utc),
        horizon_minutes=row.horizon_minutes,
        score=row.score,
        value_numeric=row.value_numeric,
        label=row.label,
        confidence=row.confidence,
        status=row.status,
        model_name=row.model_name if legacy else None,
        model_version=row.model_version if legacy else None,
        details=(row.details_json or {}) if legacy else {},
    )


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


@router.get("/latest", response_model=ForecastLatestResponse)
def forecast_latest(
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> ForecastLatestResponse:
    effective_node = node
    if effective_node is None:
        node_row = session.execute(
            select(EdgeNode).order_by(EdgeNode.last_seen_utc.desc().nullslast()).limit(1)
        ).scalars().first()
        effective_node = node_row.node_id if node_row else None

    if effective_node is None:
        return ForecastLatestResponse(node_id=None, computed_at_utc=None, items=[])

    stmt = (
        select(ForecastResult)
        .where(ForecastResult.node_id == effective_node)
        .distinct(ForecastResult.forecast_type)
        .order_by(ForecastResult.forecast_type, ForecastResult.computed_at_utc.desc())
    )
    rows = session.execute(stmt).scalars().all()
    items = [_forecast_to_response(row) for row in rows]
    latest_computed = max((row.computed_at_utc for row in rows), default=None)
    return ForecastLatestResponse(
        node_id=effective_node,
        computed_at_utc=_iso(latest_computed),
        items=items,
    )