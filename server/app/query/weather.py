from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.ops import WeatherQualityEvent
from app.models.weather import WeatherMinuteSummary, WeatherSample
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

_LAST_VALUE_AGG = {
    "latest_wind_dir_deg": (
        "minute_utc",
        "latest_wind_dir_deg IS NOT NULL AND latest_wind_dir_deg <> 0"
    ),
}


def _iso(dt) -> str:
    return dt.isoformat()


@router.get("/latest", response_model=LatestResponse)
def weather_latest(
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> LatestResponse:
    sample_stmt = select(WeatherSample).order_by(WeatherSample.ts_pi_utc.desc()).limit(1)
    if node:
        sample_stmt = sample_stmt.where(WeatherSample.node_id == node)
    sample_row = session.execute(sample_stmt).scalars().first()
    if sample_row is not None:
        return LatestResponse(node_id=node, minute=_sample_to_latest_dict(sample_row))

    summary_stmt = select(WeatherMinuteSummary).order_by(WeatherMinuteSummary.minute_utc.desc()).limit(1)
    if node:
        summary_stmt = summary_stmt.where(WeatherMinuteSummary.node_id == node)
    summary_row = session.execute(summary_stmt).scalars().first()
    if summary_row is None:
        return LatestResponse(node_id=node, minute=None)
    return LatestResponse(node_id=node, minute=_summary_to_dict(summary_row))


def _sample_to_latest_dict(row: WeatherSample) -> dict[str, Any]:
    return {
        "minute_utc": row.ts_pi_utc.isoformat() if row.ts_pi_utc else None,
        "source": row.source,
        "device": row.device,
        "status": None,
        "degraded": None,
        "sample_count": 1,
        "temperature_avg": row.temperature_c,
        "temperature_min": row.temperature_c,
        "temperature_max": row.temperature_c,
        "humidity_avg": row.humidity_pct,
        "pressure_avg": row.pressure_hpa,
        "illuminance_avg": row.illuminance_lux,
        "rain_max": row.rain_mm,
        "wind_speed_avg": row.wind_speed_ms,
        "wind_speed_max": row.wind_speed_ms,
        "latest_wind_dir_deg": row.wind_dir_deg,
    }


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
    limit: int = Query(default=3000, ge=100, le=10000),
    session: Session = Depends(get_session),
) -> HistoryResponse:
    from_dt, to_dt = parse_range(from_, to, interval)

    if interval == "raw":
        series = _raw_series(session, from_dt, to_dt, node, limit)
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


def _raw_series(session, from_dt, to_dt, node, limit: int) -> list[dict[str, Any]]:
    stmt = (
        select(WeatherSample)
        .where(WeatherSample.ts_pi_utc >= from_dt)
        .where(WeatherSample.ts_pi_utc < to_dt)
    )
    if node:
        stmt = stmt.where(WeatherSample.node_id == node)
    stmt = stmt.order_by(WeatherSample.ts_pi_utc.desc()).limit(limit)
    rows = list(session.execute(stmt).scalars())
    rows.reverse()
    out = []
    for row in rows:
        out.append(
            {
                "bucket": row.ts_pi_utc.isoformat() if row.ts_pi_utc else None,
                "edge_id": row.edge_id,
                "source": row.source,
                "device": row.device,
                "sensor": row.sensor,
                "temperature_c": row.temperature_c,
                "humidity_pct": row.humidity_pct,
                "pressure_hpa": row.pressure_hpa,
                "illuminance_lux": row.illuminance_lux,
                "rain_mm": row.rain_mm,
                "wind_speed_ms": row.wind_speed_ms,
                "wind_dir_code": row.wind_dir_code,
                "wind_dir_deg": row.wind_dir_deg,
                "created_at_utc": row.created_at_utc.isoformat() if row.created_at_utc else None,
            }
        )
    return out


def _bucketed_series(session, interval, from_dt, to_dt, node) -> list[dict[str, Any]]:
    bucket = bucket_expr(interval, "minute_utc")
    numeric_agg_cols = [
        f"{fn}({col}) AS {col}" for col, fn in _NUMERIC_AGG.items()
    ]
    last_value_agg_cols = [
        (
            f"(ARRAY_AGG({col} ORDER BY {order_col} DESC) "
            f"FILTER (WHERE {filter_expr}))[1] AS {col}"
        )
        for col, (order_col, filter_expr) in _LAST_VALUE_AGG.items()
    ]
    agg_cols = ", ".join([*numeric_agg_cols, *last_value_agg_cols])
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
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    # Quality page reads aggregated minute summaries + quality-event rows, not
    # raw sensor samples. So it should support longer dashboard ranges such as
    # 30d and 365d without tripping the raw-series 7-day safety cap.
    from_dt, to_dt = parse_range(from_, to, "1h")

    summary_stmt = (
        select(
            func.count(WeatherMinuteSummary.id).label("total_minutes"),
            func.sum(
                text("CASE WHEN status = 'ok' THEN 1 ELSE 0 END")
            ).label("ok_count"),
            func.sum(
                text("CASE WHEN status = 'warn' THEN 1 ELSE 0 END")
            ).label("warn_count"),
            func.sum(
                text("CASE WHEN status = 'invalid' THEN 1 ELSE 0 END")
            ).label("invalid_count"),
        )
        .where(WeatherMinuteSummary.minute_utc >= from_dt)
        .where(WeatherMinuteSummary.minute_utc < to_dt)
    )
    if node:
        summary_stmt = summary_stmt.where(WeatherMinuteSummary.node_id == node)
    summary_row = session.execute(summary_stmt).mappings().one()

    event_where = ["created_at_utc >= :from_dt", "created_at_utc < :to_dt"]
    event_params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    if node:
        event_where.append("node_id = :node")
        event_params["node"] = node

    event_summary_sql = text(
        f"""
        WITH per_minute AS (
            SELECT
                minute_utc,
                MAX(
                    CASE
                        WHEN quality_status = 'invalid' THEN 2
                        WHEN quality_status = 'warn' THEN 1
                        ELSE 0
                    END
                ) AS severity
            FROM weather_quality_events
            WHERE {' AND '.join(event_where)}
            GROUP BY minute_utc
        )
        SELECT
            COUNT(*) FILTER (WHERE severity = 1) AS warn_minutes,
            COUNT(*) FILTER (WHERE severity = 2) AS invalid_minutes
        FROM per_minute
        """
    )
    event_summary_row = session.execute(event_summary_sql, event_params).mappings().one()

    count_stmt = (
        select(func.count())
        .select_from(WeatherQualityEvent)
        .where(WeatherQualityEvent.created_at_utc >= from_dt)
        .where(WeatherQualityEvent.created_at_utc < to_dt)
    )
    if node:
        count_stmt = count_stmt.where(WeatherQualityEvent.node_id == node)
    if status:
        count_stmt = count_stmt.where(WeatherQualityEvent.quality_status == status)
    total_items = int(session.execute(count_stmt).scalar() or 0)
    total_pages = max(1, math.ceil(total_items / page_size))
    current_page = min(page, total_pages)
    offset = (current_page - 1) * page_size

    stmt = (
        select(WeatherQualityEvent)
        .where(WeatherQualityEvent.created_at_utc >= from_dt)
        .where(WeatherQualityEvent.created_at_utc < to_dt)
        .order_by(WeatherQualityEvent.created_at_utc.desc())
        .limit(page_size)
        .offset(offset)
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
    summary = {
        "total_minutes": int(summary_row.get("total_minutes") or 0),
        "counts": {
            "ok": int(summary_row.get("ok_count") or 0),
            "warn": int(summary_row.get("warn_count") or 0),
            "invalid": int(summary_row.get("invalid_count") or 0),
        },
        "event_minutes": {
            "warn": int(event_summary_row.get("warn_minutes") or 0),
            "invalid": int(event_summary_row.get("invalid_minutes") or 0),
        },
    }

    effective_invalid = max(summary["counts"]["invalid"], summary["event_minutes"]["invalid"])
    effective_warn = max(summary["counts"]["warn"], summary["event_minutes"]["warn"])
    if effective_invalid + effective_warn > summary["total_minutes"]:
        overflow = effective_invalid + effective_warn - summary["total_minutes"]
        effective_warn = max(0, effective_warn - overflow)
    effective_ok = max(0, summary["total_minutes"] - effective_warn - effective_invalid)
    summary["effective_counts"] = {
        "ok": effective_ok,
        "warn": effective_warn,
        "invalid": effective_invalid,
    }

    return {
        "node_id": node,
        "items": items,
        "summary": summary,
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
