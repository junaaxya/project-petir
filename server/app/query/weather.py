from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from petir_contracts import DailyForecastItem, DailyForecastResponse

from app.db import get_session
from app.models.ops import WeatherQualityEvent
from app.models.weather import WeatherMinuteSummary, WeatherSample
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
from app.services.daily_forecast import calculate_daily_forecast, forecast_ranges_wib
from app.settings import settings

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

_DAILY_FORECAST_CACHE_TTL_SECONDS = 60.0
_DAILY_FORECAST_MIN_POINTS = 30
_DAILY_FORECAST_STALE_AFTER = timedelta(minutes=30)
_INTERVAL_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}
_daily_forecast_cache: dict[tuple[str, str], tuple[float, DailyForecastResponse]] = {}
_daily_forecast_cache_lock = Lock()


def _iso(dt) -> str:
    return dt.isoformat()


def _public_sensor_metadata(source: Optional[str], device: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if settings.public_data_mode == "public_safe":
        return ("weather_station", "weather_sensor")
    return source, device


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
    source, device = _public_sensor_metadata(row.source, row.device)
    return {
        "minute_utc": row.ts_pi_utc.isoformat() if row.ts_pi_utc else None,
        "source": source,
        "device": device,
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
    source, device = _public_sensor_metadata(row.source, row.device)
    return {
        "minute_utc": row.minute_utc.isoformat() if row.minute_utc else None,
        "source": source,
        "device": device,
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


def _get_cached_daily_forecast(key: tuple[str, str]) -> DailyForecastResponse | None:
    now_monotonic = monotonic()
    with _daily_forecast_cache_lock:
        cached = _daily_forecast_cache.get(key)
        if cached is None:
            return None
        expires_at, response = cached
        if expires_at <= now_monotonic:
            _daily_forecast_cache.pop(key, None)
            return None
        return response


def _set_cached_daily_forecast(key: tuple[str, str], response: DailyForecastResponse) -> None:
    with _daily_forecast_cache_lock:
        if len(_daily_forecast_cache) >= 64:
            _daily_forecast_cache.clear()
        _daily_forecast_cache[key] = (monotonic() + _DAILY_FORECAST_CACHE_TTL_SECONDS, response)


def clear_daily_forecast_cache() -> None:
    """Clear only the short-lived in-memory forecast cache."""
    with _daily_forecast_cache_lock:
        _daily_forecast_cache.clear()


def _validate_history_cost(from_dt: datetime, to_dt: datetime, interval: str) -> None:
    if interval == "raw":
        rows_per_minute = settings.weather_raw_estimated_rows_per_minute
        limit = QueryCostLimit(
            unit_seconds=max(1, 60 // rows_per_minute),
            max_units=settings.weather_raw_max_estimated_rows,
            max_span=timedelta(days=7),
        )
    else:
        limit = QueryCostLimit(
            unit_seconds=_INTERVAL_SECONDS[interval],
            max_units=settings.history_max_buckets,
            max_span=timedelta(days=366),
        )
    validate_estimated_cost(from_dt, to_dt, limit)


def _quality_event_to_dict(row: WeatherQualityEvent) -> dict[str, Any]:
    common = {
        "minute_utc": row.minute_utc.isoformat() if row.minute_utc else None,
        "quality_status": row.quality_status,
        "created_at_utc": row.created_at_utc.isoformat() if row.created_at_utc else None,
    }
    if settings.public_data_mode == "public_safe":
        return {
            "event_id": opaque_event_id(
                "weather-quality", row.node_id, row.db_epoch, row.edge_id
            ),
            **common,
        }
    return {
        "edge_id": row.edge_id,
        **common,
        "reason_codes": row.reason_codes,
        "message": row.message,
    }


@router.get("/daily-forecast", response_model=DailyForecastResponse)
def weather_daily_forecast(
    node: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> DailyForecastResponse:
    now = datetime.now(timezone.utc)
    ranges = forecast_ranges_wib(now)
    cache_key = (node or "__all__", ranges.local_date)
    cached = _get_cached_daily_forecast(cache_key)
    if cached is not None:
        return cached

    where = ["minute_utc >= :from_dt", "minute_utc < :to_dt"]
    params: dict[str, Any] = {
        "from_dt": ranges.baseline_start_utc,
        "to_dt": ranges.tomorrow_start_utc,
    }
    if node:
        where.append("node_id = :node")
        params["node"] = node

    # This endpoint is deliberately read-only: a single aggregate SELECT and
    # no writes, migrations, seeds, or forecast-result persistence.
    stmt = text(
        f"""
        SELECT
            minute_utc AS bucket,
            AVG(temperature_avg) AS temperature_avg,
            AVG(humidity_avg) AS humidity_avg,
            AVG(pressure_avg) AS pressure_avg,
            AVG(illuminance_avg) AS illuminance_avg,
            MAX(rain_max) AS rain_max,
            AVG(wind_speed_avg) AS wind_speed_avg,
            MAX(wind_speed_max) AS wind_speed_max
        FROM weather_minute_summary
        WHERE {' AND '.join(where)}
        GROUP BY minute_utc
        ORDER BY minute_utc ASC
        """
    )
    rows = [dict(row) for row in session.execute(stmt, params).mappings().all()]
    baseline_rows = [row for row in rows if row["bucket"] < ranges.today_start_utc]
    today_rows = [row for row in rows if row["bucket"] >= ranges.today_start_utc]
    latest_bucket = max((row["bucket"] for row in today_rows), default=None)
    if len(today_rows) < _DAILY_FORECAST_MIN_POINTS:
        status = "insufficient_data"
    elif latest_bucket is None or latest_bucket < now - _DAILY_FORECAST_STALE_AFTER:
        status = "stale_data"
    else:
        status = "available"
    snapshots = (
        calculate_daily_forecast(today_rows, baseline_rows, now=now)
        if status == "available"
        else []
    )

    response = DailyForecastResponse(
        node_id=node,
        forecast_date_wib=ranges.local_date,
        today_label=ranges.today_label,
        computed_at_utc=now.isoformat(),
        status=status,
        sample_count=len(today_rows),
        latest_sample_utc=latest_bucket.isoformat() if latest_bucket else None,
        items=[
            DailyForecastItem(
                kind=item.kind,
                label=item.label,
                score=item.score,
                level=item.level,
                peak_window=item.peak_window,
                reasons=item.reasons,
            )
            for item in snapshots
        ],
    )
    _set_cached_daily_forecast(cache_key, response)
    return response


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
    _validate_history_cost(from_dt, to_dt, interval)
    apply_statement_timeout(session, settings.query_statement_timeout_ms)

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
        item = {
            "bucket": row.ts_pi_utc.isoformat() if row.ts_pi_utc else None,
            "temperature_c": row.temperature_c,
            "humidity_pct": row.humidity_pct,
            "pressure_hpa": row.pressure_hpa,
            "illuminance_lux": row.illuminance_lux,
            "rain_mm": row.rain_mm,
            "wind_speed_ms": row.wind_speed_ms,
            "wind_dir_deg": row.wind_dir_deg,
        }
        if settings.public_data_mode == "legacy_full":
            item.update(
                {
                    "edge_id": row.edge_id,
                    "source": row.source,
                    "device": row.device,
                    "sensor": row.sensor,
                    "wind_dir_code": row.wind_dir_code,
                    "created_at_utc": row.created_at_utc.isoformat()
                    if row.created_at_utc
                    else None,
                }
            )
        out.append(item)
    return out


def _bucketed_series(session, interval, from_dt, to_dt, node) -> list[dict[str, Any]]:
    bucket = bucket_expr(interval, "minute_utc")
    numeric_agg_cols = [
        f"{fn}({col}) AS {col}" for col, fn in _NUMERIC_AGG.items()
    ]
    agg_cols = ", ".join(numeric_agg_cols)
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
    dominant_directions = _dominant_wind_directions(
        session, interval, from_dt, to_dt, node
    )
    out = []
    for r in rows:
        d = dict(r)
        b = d.get("bucket")
        d["latest_wind_dir_deg"] = dominant_directions.get(b)
        d["bucket"] = b.isoformat() if isinstance(b, datetime) else b
        out.append(d)
    return out


def _dominant_wind_directions(
    session, interval, from_dt, to_dt, node
) -> dict[Any, float]:
    use_raw_samples = (to_dt - from_dt) <= timedelta(days=7)
    if use_raw_samples:
        table = "weather_samples"
        time_column = "ts_pi_utc"
        direction_column = "wind_dir_deg"
        speed_column = "wind_speed_ms"
    else:
        table = "weather_minute_summary"
        time_column = "minute_utc"
        direction_column = "latest_wind_dir_deg"
        speed_column = "wind_speed_avg"

    bucket = bucket_expr(interval, time_column)
    sector = (
        f"MOD(MOD(FLOOR(({direction_column} + 22.5) / 45)::integer, 8) + 8, 8)"
    )
    where = [
        f"{time_column} >= :from_dt",
        f"{time_column} < :to_dt",
        f"{direction_column} IS NOT NULL",
        f"COALESCE({speed_column}, 0) > 0",
    ]
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    if node:
        where.append("node_id = :node")
        params["node"] = node

    sql = text(
        f"""
        WITH direction_counts AS (
            SELECT
                {bucket} AS bucket,
                {sector} AS sector,
                COUNT(*) AS direction_count,
                SUM({speed_column}) AS total_speed
            FROM {table}
            WHERE {' AND '.join(where)}
            GROUP BY 1, 2
        ), ranked AS (
            SELECT
                bucket,
                sector,
                ROW_NUMBER() OVER (
                    PARTITION BY bucket
                    ORDER BY direction_count DESC, total_speed DESC, sector ASC
                ) AS rank
            FROM direction_counts
        )
        SELECT bucket, sector * 45.0 AS direction_deg
        FROM ranked
        WHERE rank = 1
        """
    )
    return {
        row["bucket"]: float(row["direction_deg"])
        for row in session.execute(sql, params).mappings().all()
    }


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
    validate_estimated_cost(
        from_dt,
        to_dt,
        QueryCostLimit(
            unit_seconds=60,
            max_units=settings.quality_max_estimated_minute_rows,
            max_span=timedelta(days=366),
        ),
    )
    validate_page_window(
        page=page, page_size=page_size, max_rows=settings.query_max_page_rows
    )
    apply_statement_timeout(session, settings.query_statement_timeout_ms)

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
        items.append(_quality_event_to_dict(row))
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
