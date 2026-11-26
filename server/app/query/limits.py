from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class QueryCostLimit:
    unit_seconds: int
    max_units: int
    max_span: timedelta


def validate_estimated_cost(
    from_dt: datetime,
    to_dt: datetime,
    limit: QueryCostLimit,
) -> int:
    span = to_dt - from_dt
    if span > limit.max_span:
        raise HTTPException(
            status_code=416,
            detail={
                "code": "RANGE_TOO_LARGE",
                "message": f"query range exceeds {limit.max_span.days} days",
            },
        )
    estimated_units = math.ceil(span.total_seconds() / limit.unit_seconds)
    if estimated_units > limit.max_units:
        raise HTTPException(
            status_code=416,
            detail={
                "code": "QUERY_COST_TOO_HIGH",
                "message": "requested resolution is too expensive for this date range; use a larger interval",
            },
        )
    return estimated_units


def validate_page_window(*, page: int, page_size: int, max_rows: int) -> None:
    if page * page_size > max_rows:
        raise HTTPException(
            status_code=416,
            detail={
                "code": "PAGE_WINDOW_TOO_LARGE",
                "message": f"pagination is limited to the first {max_rows} rows; narrow the date range",
            },
        )


def apply_statement_timeout(session: Session, timeout_ms: int) -> None:
    session.execute(
        text("SELECT set_config('statement_timeout', :timeout, true)"),
        {"timeout": f"{timeout_ms}ms"},
    )
