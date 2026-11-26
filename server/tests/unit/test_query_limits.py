from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.query.limits import (
    QueryCostLimit,
    validate_estimated_cost,
    validate_page_window,
)


def test_query_cost_rejects_estimate_before_session_is_used():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(HTTPException) as exc:
        validate_estimated_cost(
            start,
            start + timedelta(days=2),
            QueryCostLimit(unit_seconds=60, max_units=1000, max_span=timedelta(days=10)),
        )
    assert exc.value.status_code == 416
    assert exc.value.detail["code"] == "QUERY_COST_TOO_HIGH"


def test_page_window_is_bounded():
    validate_page_window(page=100, page_size=100, max_rows=10_000)
    with pytest.raises(HTTPException) as exc:
        validate_page_window(page=101, page_size=100, max_rows=10_000)
    assert exc.value.detail["code"] == "PAGE_WINDOW_TOO_LARGE"