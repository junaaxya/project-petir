from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.query.freshness import age_seconds, status_for_age


def test_age_none_when_no_ts():
    assert age_seconds(None) is None


def test_status_no_data():
    assert status_for_age(None) == "no_data"


def test_status_fresh_stale_offline():
    assert status_for_age(10, send_interval_s=15) == "fresh"
    assert status_for_age(40, send_interval_s=15) == "stale"
    assert status_for_age(200, send_interval_s=15) == "offline"


def test_age_seconds_positive():
    past = datetime.now(timezone.utc) - timedelta(seconds=30)
    age = age_seconds(past)
    assert age is not None and 29 <= age <= 40


def test_age_handles_naive_datetime():
    past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10)
    age = age_seconds(past)
    assert age is not None and age >= 9
