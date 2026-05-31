from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.ops import WeatherQualityEvent
from app.models.weather import WeatherMinuteSummary
from app.query.auth import verify_dashboard_user
from app.query.downsample import bucket_expr, parse_range
from app.schemas.query import HistoryMeta, HistoryResponse, LatestResponse

router = APIRouter(prefix="/api/weather", tags=["weather"], dependencies=[Depends(verify_dashboard_user)])

_NUMERIC_AGG = {
    "temperature_avg": "avg",
    "temperature_min": "min",
    "temperature_max": "max",
    "humidity_avg": "avg",
    "pressure_avg": "avg",
    "illuminance_avg": "avg",
    "rain_max": "max",
    "wind_speed_avg": "avg",
    "wind_speed_max": "max",
    "sample_count": "sum",
}


def _iso(dt) -> str:
    return dt.isoformat()


@router.get("/latest", response_model=LatestResponse)
def weather_latest(
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> LatestResponse:
    stmt = select(WeatherMinuteSummary).order_by(WeatherMinuteSummary.minute_utc.desc()).limit(1)
    if node:
        stmt = stmt.where(WeatherMinuteSummary.node_id == node)
    row = session.execute(stmt).scalars().first()
    if row is None:
        return LatestResponse(node_id=node, minute=None)
    return LatestResponse(node_id=node, minute=_summary_to_dict(row))


def _summary_to_dict(row: WeatherMinuteSummary) -> dict[str, Any]:
    return {
        "minute_utc": row.minute_utc.isoformat() if row.minute_utc else None,
        "source": row.source,
        "device": row.device,
        "status": row.status,
        "degraded": row.degraded,
        "sample_count": row.sample_count,
        "temperature_avg": row.temperature_avg,
        "temperature_min": row.temperature_min,
        "temperature_max": row.temperature_max,
        "humidity_avg": row.humidity_avg,
        "pressure_avg": row.pressure_avg,
        "illuminance_avg": row.illuminance_avg,
        "rain_max": row.rain_max,
        "wind_speed_avg": row.wind_speed_avg,
        "wind_speed_max": row.wind_speed_max,
        "latest_wind_dir_deg": row.latest_wind_dir_deg,
    }


@router.get("/history", response_model=HistoryResponse)
def weather_history(
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
        from_utc=_iso(from_dt),
        to_utc=_iso(to_dt),
        series=series,
        meta=HistoryMeta(count=len(series), downsampled=downsampled),
    )


def _raw_series(session, from_dt, to_dt, node) -> list[dict[str, Any]]:
    stmt = (
        select(WeatherMinuteSummary)
        .where(WeatherMinuteSummary.minute_utc >= from_dt)
        .where(WeatherMinuteSummary.minute_utc < to_dt)
        .order_by(WeatherMinuteSummary.minute_utc.asc())
    )
    if node:
        stmt = stmt.where(WeatherMinuteSummary.node_id == node)
    out = []
    for row in session.execute(stmt).scalars():
        d = _summary_to_dict(row)
        d["bucket"] = d.pop("minute_utc")
        out.append(d)
    return out


def _bucketed_series(session, interval, from_dt, to_dt, node) -> list[dict[str, Any]]:
    bucket = bucket_expr(interval, "minute_utc")
    agg_cols = ", ".join(
        f"{fn}({col}) AS {col}" for col, fn in _NUMERIC_AGG.items()
    )
    where = ["minute_utc >= :from_dt", "minute_utc < :to_dt"]
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    if node:
        where.append("node_id = :node")
        params["node"] = node
    sql = text(
        f"SELECT {bucket} AS bucket, {agg_cols} "
        f"FROM weather_minute_summary "
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


@router.get("/quality-events")
def weather_quality_events(
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    node: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    from_dt, to_dt = parse_range(from_, to, "raw")
    stmt = (
        select(WeatherQualityEvent)
        .where(WeatherQualityEvent.created_at_utc >= from_dt)
        .where(WeatherQualityEvent.created_at_utc < to_dt)
        .order_by(WeatherQualityEvent.created_at_utc.desc())
        .limit(limit)
    )
    if node:
        stmt = stmt.where(WeatherQualityEvent.node_id == node)
    if status:
        stmt = stmt.where(WeatherQualityEvent.quality_status == status)
    items = []
    for row in session.execute(stmt).scalars():
        items.append(
            {
                "edge_id": row.edge_id,
                "minute_utc": row.minute_utc.isoformat() if row.minute_utc else None,
                "quality_status": row.quality_status,
                "reason_codes": row.reason_codes,
                "message": row.message,
                "created_at_utc": row.created_at_utc.isoformat() if row.created_at_utc else None,
            }
        )
    return {"node_id": node, "items": items, "meta": {"count": len(items)}}
