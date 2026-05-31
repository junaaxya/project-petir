from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

VALID_INTERVALS = {"raw", "1m", "5m", "15m", "1h"}

_INTERVAL_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}

_RAW_MAX_RANGE = timedelta(days=7)


def _parse_dt(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_PARAM", "message": f"invalid timestamp: {value}"},
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_range(
    from_s: str | None, to_s: str | None, interval: str
) -> tuple[datetime, datetime]:
    if interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_PARAM", "message": f"unknown interval: {interval}"},
        )
    now = datetime.now(timezone.utc)
    to_dt = _parse_dt(to_s) if to_s else now
    from_dt = _parse_dt(from_s) if from_s else to_dt - timedelta(hours=24)
    if from_dt >= to_dt:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_RANGE", "message": "from must be < to"},
        )
    if interval == "raw" and (to_dt - from_dt) > _RAW_MAX_RANGE:
        raise HTTPException(
            status_code=416,
            detail={"code": "RANGE_TOO_LARGE", "message": "raw range exceeds 7 days"},
        )
    return from_dt, to_dt


def bucket_expr(interval: str, column: str) -> str:
    # Floor each timestamp to its interval boundary via epoch arithmetic so the
    # bucket key is deterministic; 1h uses date_trunc for a clean hour boundary.
    if interval == "1h":
        return f"date_trunc('hour', {column})"
    seconds = _INTERVAL_SECONDS[interval]
    return f"to_timestamp(floor(extract(epoch from {column}) / {seconds}) * {seconds})"
