from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from typing import Any, cast
from unittest.mock import patch

from app.services.daily_forecast import (
    calculate_daily_forecast,
    forecast_ranges_wib,
    level_from_score,
)


class _FakeMappings:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return _FakeMappings(self.rows)


class _FakeSession:
    def __init__(self, rows=None) -> None:
        self.sql = ""
        self.params = {}
        self.rows = rows or []

    def execute(self, statement, params):
        self.sql = str(statement)
        self.params = params
        return _FakeResult(self.rows)


FIXED_NOW = datetime(2026, 8, 20, 6, 30, tzinfo=timezone.utc)


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW if tz is not None else FIXED_NOW.replace(tzinfo=None)


def _forecast_rows(count: int, latest_age_minutes: int) -> list[dict[str, Any]]:
    latest = FIXED_NOW - timedelta(minutes=latest_age_minutes)
    return [
        {
            "bucket": latest - timedelta(minutes=count - index - 1),
            "temperature_avg": 28.0,
            "humidity_avg": 80.0,
            "pressure_avg": 1008.0,
            "illuminance_avg": 500.0,
            "rain_max": 0.0,
            "wind_speed_avg": 1.0,
            "wind_speed_max": 2.0,
        }
        for index in range(count)
    ]


class DailyForecastUnitTests(unittest.TestCase):
    def test_ranges_follow_wib_calendar(self) -> None:
        now = datetime(2026, 8, 20, 6, 30, tzinfo=timezone.utc)
        ranges = forecast_ranges_wib(now)

        self.assertEqual(ranges.today_label, "20-08-2026")
        self.assertEqual(ranges.today_start_utc.isoformat(), "2026-08-19T17:00:00+00:00")
        self.assertEqual(ranges.tomorrow_start_utc.isoformat(), "2026-08-20T17:00:00+00:00")
        self.assertEqual(ranges.baseline_start_utc.isoformat(), "2026-08-12T17:00:00+00:00")

    def test_empty_input_returns_no_forecast(self) -> None:
        now = datetime(2026, 8, 20, 6, 30, tzinfo=timezone.utc)
        items = calculate_daily_forecast([], [], now=now)

        self.assertEqual(items, [])

    def test_level_thresholds_match_existing_frontend(self) -> None:
        self.assertEqual(level_from_score("petir", 2.49), "rendah")
        self.assertEqual(level_from_score("petir", 2.5), "sedang")
        self.assertEqual(level_from_score("petir", 5), "tinggi")
        self.assertEqual(level_from_score("hujan", 4.5), "tinggi")
        self.assertEqual(level_from_score("angin", 1.99), "rendah")
        self.assertEqual(level_from_score("angin", 2), "sedang")
        self.assertEqual(level_from_score("angin", 3.5), "tinggi")

    def test_naive_now_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            forecast_ranges_wib(datetime(2026, 8, 20, 6, 30))

    def test_endpoint_uses_read_only_select(self) -> None:
        from app.query.weather import clear_daily_forecast_cache, weather_daily_forecast

        clear_daily_forecast_cache()
        session = _FakeSession()
        response = weather_daily_forecast(node=None, session=cast(Any, session))

        self.assertTrue(session.sql.strip().upper().startswith("SELECT"))
        self.assertNotIn("DELETE", session.sql.upper())
        self.assertNotIn("TRUNCATE", session.sql.upper())
        self.assertNotIn("DROP", session.sql.upper())
        self.assertEqual(response.status, "insufficient_data")
        self.assertEqual(response.items, [])
        self.assertEqual(response.sample_count, 0)

    def test_endpoint_requires_thirty_fresh_points(self) -> None:
        from app.query.weather import clear_daily_forecast_cache, weather_daily_forecast

        for count, expected_status in ((29, "insufficient_data"), (30, "available")):
            clear_daily_forecast_cache()
            session = _FakeSession(_forecast_rows(count, latest_age_minutes=1))
            with patch("app.query.weather.datetime", _FixedDateTime):
                response = weather_daily_forecast(node=f"node-{count}", session=cast(Any, session))

            self.assertEqual(response.status, expected_status)
            self.assertEqual(response.sample_count, count)
            if expected_status == "insufficient_data":
                self.assertEqual(response.items, [])
            else:
                self.assertEqual(len(response.items), 3)

    def test_endpoint_marks_old_telemetry_stale_without_items(self) -> None:
        from app.query.weather import clear_daily_forecast_cache, weather_daily_forecast

        clear_daily_forecast_cache()
        session = _FakeSession(_forecast_rows(30, latest_age_minutes=31))
        with patch("app.query.weather.datetime", _FixedDateTime):
            response = weather_daily_forecast(node="stale-node", session=cast(Any, session))

        self.assertEqual(response.status, "stale_data")
        self.assertEqual(response.sample_count, 30)
        self.assertEqual(response.items, [])


if __name__ == "__main__":
    unittest.main()
