from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from petir_contracts import (
    LightningEventsExportResponse,
    LightningEventsResponse,
)

from app.db import get_session
from app.models.lightning import LightningEvent, LightningMinuteSummary
from app.query.auth import verify_dashboard_user
from app.query.downsample import bucket_expr, parse_range
from app.query.limits import (
    QueryCostLimit,
    apply_statement_timeout,
    validate_estimated_cost,
    validate_page_window,
)
from app.query.public_data import opaque_event_id
from app.schemas.query import HistoryMeta, HistoryResponse, LatestResponse
from app.settings import settings

router = APIRouter(prefix="/api/lightning", tags=["lightning"], dependencies=[Depends(verify_dashboard_user)])


def _summary_to_dict(row: LightningMinuteSummary) -> dict[str, Any]:
    source = "lightning_station" if settings.public_data_mode == "public_safe" else row.source
    device = "lightning_sensor" if settings.public_data_mode == "public_safe" else row.device
    return {
        "minute_utc": row.minute_utc.isoformat() if row.minute_utc else None,
        "source": source,
        "device": device,
        "status": row.status,
        "lightning_count": row.lightning_count,
        "disturber_count": row.disturber_count,
        "noise_window_count": row.noise_window_count,
        "noise_event_count": row.noise_event_count,
        "last_event_ts_utc": row.last_event_ts_utc.isoformat() if row.last_event_ts_utc else None,
        "last_distance_km": row.last_distance_km,
        "max_energy_raw": row.max_energy_raw if settings.public_data_mode == "legacy_full" else None,
    }


def _event_to_dict(row: LightningEvent) -> dict[str, Any]:
    if settings.public_data_mode == "public_safe":
        return {
            "event_id": opaque_event_id(
                "lightning", row.node_id, row.db_epoch, row.edge_id
            ),
            "ts_pi_utc": row.ts_pi_utc.isoformat() if row.ts_pi_utc else None,
            "event_type": row.event_type,
            "distance_km": row.distance_km,
        }
    source = "lightning_station" if settings.public_data_mode == "public_safe" else row.source
    device = "lightning_sensor" if settings.public_data_mode == "public_safe" else row.device
    return {
        "edge_id": row.edge_id,
        "ts_pi_utc": row.ts_pi_utc.isoformat() if row.ts_pi_utc else None,
        "event_type": row.event_type,
        "distance_km": row.distance_km,
        "energy_raw": row.energy_raw,
        "noise_level": row.noise_level,
        "source": source,
        "device": device,
    }


@router.get("/latest", response_model=LatestResponse)
def lightning_latest(
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> LatestResponse:
    stmt = (
        select(LightningMinuteSummary)
        .order_by(LightningMinuteSummary.minute_utc.desc())
        .limit(1)
    )
    if node:
        stmt = stmt.where(LightningMinuteSummary.node_id == node)
    row = session.execute(stmt).scalars().first()
    if row is None:
        return LatestResponse(node_id=node, minute=None)
    return LatestResponse(node_id=node, minute=_summary_to_dict(row))


_NUMERIC_AGG = {
    "lightning_count": "sum",
    "disturber_count": "sum",
    "noise_window_count": "sum",
    "noise_event_count": "sum",
    "max_energy_raw": "max",
}

_EXPORT_MAX_ITEMS = 10_000
_INTERVAL_SECONDS = {"raw": 60, "1m": 60, "5m": 300, "15m": 900, "1h": 3600}


def _validate_history_cost(from_dt: datetime, to_dt: datetime, interval: str) -> None:
    validate_estimated_cost(
        from_dt,
        to_dt,
        QueryCostLimit(
            unit_seconds=_INTERVAL_SECONDS[interval],
            max_units=max(
                settings.history_max_buckets, 10_080
            ) if interval == "raw" else settings.history_max_buckets,
            max_span=timedelta(days=366),
        ),
    )


def _validate_event_cost(from_dt: datetime, to_dt: datetime, *, export: bool) -> None:
    rows_per_minute = settings.lightning_event_estimated_rows_per_minute
    validate_estimated_cost(
        from_dt,
        to_dt,
        QueryCostLimit(
            unit_seconds=max(1, 60 // rows_per_minute),
            max_units=(
                settings.lightning_export_max_estimated_rows
                if export
                else settings.lightning_event_max_estimated_rows
            ),
            max_span=timedelta(days=31 if export else 90),
        ),
    )


@router.get("/history", response_model=HistoryResponse)
def lightning_history(
    interval: str = Query(default="1h"),
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> HistoryResponse:
    from_dt, to_dt = parse_range(from_, to, interval)
    _validate_history_cost(from_dt, to_dt, interval)
    apply_statement_timeout(session, settings.query_statement_timeout_ms)

    if interval == "raw":
        series = _raw_series(session, from_dt, to_dt, node)
        downsampled = False
    else:
        series = _bucketed_series(session, interval, from_dt, to_dt, node)
        downsampled = True

    return HistoryResponse(
        node_id=node,
        interval=interval,
        from_utc=from_dt.isoformat(),
        to_utc=to_dt.isoformat(),
        series=series,
        meta=HistoryMeta(count=len(series), downsampled=downsampled),
    )


def _raw_series(session: Session, from_dt: datetime, to_dt: datetime, node: Optional[str]) -> list[dict[str, Any]]:
    stmt = (
        select(LightningMinuteSummary)
        .where(LightningMinuteSummary.minute_utc >= from_dt)
        .where(LightningMinuteSummary.minute_utc < to_dt)
        .order_by(LightningMinuteSummary.minute_utc.asc())
    )
    if node:
        stmt = stmt.where(LightningMinuteSummary.node_id == node)
    out = []
    for row in session.execute(stmt).scalars():
        d = _summary_to_dict(row)
        d["bucket"] = d.pop("minute_utc")
        out.append(d)
    return out


def _bucketed_series(
    session: Session, interval: str, from_dt: datetime, to_dt: datetime, node: Optional[str]
) -> list[dict[str, Any]]:
    bucket = bucket_expr(interval, "minute_utc")
    numeric_agg = _NUMERIC_AGG
    if settings.public_data_mode == "public_safe":
        numeric_agg = {
            key: value for key, value in _NUMERIC_AGG.items() if key != "max_energy_raw"
        }
    agg_cols = ", ".join(f"{fn}({col}) AS {col}" for col, fn in numeric_agg.items())
    where = ["minute_utc >= :from_dt", "minute_utc < :to_dt"]
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    if node:
        where.append("node_id = :node")
        params["node"] = node
    sql = text(
        f"SELECT {bucket} AS bucket, {agg_cols} "
        f"FROM lightning_minute_summary "
        f"WHERE {' AND '.join(where)} "
        f"GROUP BY bucket ORDER BY bucket ASC"
    )
    rows = session.execute(sql, params).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        b = d.get("bucket")
        d["bucket"] = b.isoformat() if isinstance(b, datetime) else b
        out.append(d)
    return out


@router.get(
    "/events",
    response_model=LightningEventsResponse,
    response_model_exclude_none=True,
)
def lightning_events(
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    from_dt, to_dt = parse_range(from_, to, "1h")
    _validate_event_cost(from_dt, to_dt, export=False)
    validate_page_window(
        page=page, page_size=page_size, max_rows=settings.query_max_page_rows
    )
    apply_statement_timeout(session, settings.query_statement_timeout_ms)
    count_stmt = (
        select(text("COUNT(*)"))
        .select_from(LightningEvent)
        .where(LightningEvent.ts_pi_utc >= from_dt)
        .where(LightningEvent.ts_pi_utc < to_dt)
    )
    if node:
        count_stmt = count_stmt.where(LightningEvent.node_id == node)
    if event_type:
        count_stmt = count_stmt.where(LightningEvent.event_type == event_type)
    total_items = int(session.execute(count_stmt).scalar() or 0)
    total_pages = max(1, math.ceil(total_items / page_size))
    current_page = min(page, total_pages)
    offset = (current_page - 1) * page_size

    stmt = (
        select(LightningEvent)
        .where(LightningEvent.ts_pi_utc >= from_dt)
        .where(LightningEvent.ts_pi_utc < to_dt)
        .order_by(LightningEvent.ts_pi_utc.desc())
        .limit(page_size)
        .offset(offset)
    )
    if node:
        stmt = stmt.where(LightningEvent.node_id == node)
    if event_type:
        stmt = stmt.where(LightningEvent.event_type == event_type)
    items = []
    for row in session.execute(stmt).scalars():
        items.append(_event_to_dict(row))
    return {
        "node_id": node,
        "items": items,
        "meta": {
            "count": len(items),
            "page": current_page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_prev": current_page > 1,
            "has_next": current_page < total_pages,
            "requested_limit": limit,
        },
    }


@router.get(
    "/events/export",
    response_model=LightningEventsExportResponse,
    response_model_exclude_none=True,
)
def export_lightning_events(
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    from_dt, to_dt = parse_range(from_, to, "1h")
    _validate_event_cost(from_dt, to_dt, export=True)
    apply_statement_timeout(session, settings.export_statement_timeout_ms)
    stmt = (
        select(LightningEvent)
        .where(LightningEvent.ts_pi_utc >= from_dt)
        .where(LightningEvent.ts_pi_utc < to_dt)
        .order_by(LightningEvent.ts_pi_utc.desc())
        .limit(_EXPORT_MAX_ITEMS + 1)
    )
    if node:
        stmt = stmt.where(LightningEvent.node_id == node)
    if event_type:
        stmt = stmt.where(LightningEvent.event_type == event_type)

    rows = session.execute(stmt).scalars().all()
    if len(rows) > _EXPORT_MAX_ITEMS:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "EXPORT_TOO_LARGE",
                "message": f"export exceeds {_EXPORT_MAX_ITEMS} events; narrow the date range",
            },
        )
    return {
        "node_id": node,
        "items": [_event_to_dict(row) for row in rows],
        "meta": {"count": len(rows), "scope": "all_filtered"},
    }


@router.get(
    "/events/latest",
    response_model=LightningEventsResponse,
    response_model_exclude_none=True,
)
def latest_lightning_events(
    node: Optional[str] = Query(default=None),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    apply_statement_timeout(session, settings.query_statement_timeout_ms)
    count_stmt = select(text("COUNT(*)")).select_from(LightningEvent)
    if node:
        count_stmt = count_stmt.where(LightningEvent.node_id == node)
    total_items = int(session.execute(count_stmt).scalar() or 0)
    stmt = select(LightningEvent).order_by(LightningEvent.ts_pi_utc.desc()).limit(page_size)
    if node:
        stmt = stmt.where(LightningEvent.node_id == node)
    items = [_event_to_dict(row) for row in session.execute(stmt).scalars()]
    return {
        "node_id": node,
        "items": items,
        "meta": {
            "count": len(items),
            "page": 1,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": 1,
            "has_prev": False,
            "has_next": False,
            "scope": "latest",
        },
    }
