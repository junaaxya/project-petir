from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.query.downsample import bucket_expr, parse_range


def test_unknown_interval_rejected():
    with pytest.raises(HTTPException) as exc:
        parse_range(None, None, "7m")
    assert exc.value.status_code == 400


def test_from_after_to_rejected():
    with pytest.raises(HTTPException) as exc:
        parse_range("2026-05-30T10:00:00Z", "2026-05-30T09:00:00Z", "1h")
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "BAD_RANGE"


def test_raw_range_too_large_rejected():
    with pytest.raises(HTTPException) as exc:
        parse_range("2026-05-01T00:00:00Z", "2026-05-30T00:00:00Z", "raw")
    assert exc.value.status_code == 416


def test_default_range_is_24h():
    from_dt, to_dt = parse_range(None, None, "1h")
    assert abs((to_dt - from_dt).total_seconds() - 86400) < 5


def test_bucket_expr_hour_uses_date_trunc():
    assert "date_trunc('hour'" in bucket_expr("1h", "minute_utc")


def test_bucket_expr_5m_uses_epoch_floor():
    expr = bucket_expr("5m", "minute_utc")
    assert "300" in expr
    assert "floor" in expr
