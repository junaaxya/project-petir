from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.query.freshness import age_seconds, status_for_age, status_for_event, status_for_node


def test_age_none_when_no_ts():
    assert age_seconds(None) is None


def test_status_no_data():
    assert status_for_age(None) == "no_data"


def test_status_fresh_stale_offline():
    assert status_for_age(10, send_interval_s=15) == "fresh"
    assert status_for_age(40, send_interval_s=15) == "stale"
    assert status_for_age(200, send_interval_s=15) == "offline"


def test_weather_cadence_uses_minute_thresholds():
    assert status_for_age(119, send_interval_s=60) == "fresh"
    assert status_for_age(120, send_interval_s=60) == "stale"
    assert status_for_age(299, send_interval_s=60) == "stale"
    assert status_for_age(300, send_interval_s=60) == "offline"


def test_node_health_uses_sync_liveness_thresholds():
    assert status_for_node(None) == "no_data"
    assert status_for_node(59) == "fresh"
    assert status_for_node(60) == "stale"
    assert status_for_node(179) == "stale"
    assert status_for_node(180) == "offline"


def test_event_stream_silence_never_reports_offline():
    assert status_for_event(None, "fresh") == "no_data"
    assert status_for_event(999_999, "fresh") == "idle"
    assert status_for_event(999_999, "stale") == "idle"
    assert status_for_event(10, "offline") == "unknown"


def test_age_seconds_positive():
    past = datetime.now(timezone.utc) - timedelta(seconds=30)
    age = age_seconds(past)
    assert age is not None and 29 <= age <= 40


def test_age_handles_naive_datetime():
    past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10)
    age = age_seconds(past)
    assert age is not None and age >= 9
