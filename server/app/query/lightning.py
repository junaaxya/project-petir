from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.lightning import LightningEvent, LightningMinuteSummary
from app.query.auth import verify_dashboard_user
from app.query.downsample import bucket_expr, parse_range
from app.schemas.query import HistoryMeta, HistoryResponse, LatestResponse

router = APIRouter(prefix="/api/lightning", tags=["lightning"], dependencies=[Depends(verify_dashboard_user)])


def _summary_to_dict(row: LightningMinuteSummary) -> dict[str, Any]:
    return {
        "minute_utc": row.minute_utc.isoformat() if row.minute_utc else None,
        "source": row.source,
        "device": row.device,
        "status": row.status,
        "lightning_count": row.lightning_count,
        "disturber_count": row.disturber_count,
        "noise_window_count": row.noise_window_count,
        "noise_event_count": row.noise_event_count,
        "last_event_ts_utc": row.last_event_ts_utc.isoformat() if row.last_event_ts_utc else None,
        "last_distance_km": row.last_distance_km,
        "max_energy_raw": row.max_energy_raw,
    }


def _event_to_dict(row: LightningEvent) -> dict[str, Any]:
    return {
        "edge_id": row.edge_id,
        "ts_pi_utc": row.ts_pi_utc.isoformat() if row.ts_pi_utc else None,
        "event_type": row.event_type,
        "distance_km": row.distance_km,
        "energy_raw": row.energy_raw,
        "noise_level": row.noise_level,
        "source": row.source,
        "device": row.device,
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


@router.get("/history", response_model=HistoryResponse)
def lightning_history(
    interval: str = Query(default="1h"),
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> HistoryResponse:
    from_dt, to_dt = parse_range(from_, to, interval)

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
    agg_cols = ", ".join(f"{fn}({col}) AS {col}" for col, fn in _NUMERIC_AGG.items())
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


@router.get("/events")
def lightning_events(
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    from_dt, to_dt = parse_range(from_, to, "raw")
    stmt = (
        select(LightningEvent)
        .where(LightningEvent.ts_pi_utc >= from_dt)
        .where(LightningEvent.ts_pi_utc < to_dt)
        .order_by(LightningEvent.ts_pi_utc.desc())
        .limit(limit)
    )
    if node:
        stmt = stmt.where(LightningEvent.node_id == node)
    if event_type:
        stmt = stmt.where(LightningEvent.event_type == event_type)
    items = []
    for row in session.execute(stmt).scalars():
        items.append(_event_to_dict(row))
    return {"node_id": node, "items": items, "meta": {"count": len(items)}}
