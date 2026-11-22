from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Any, cast

from app.services.daily_forecast import (
    calculate_daily_forecast,
    forecast_ranges_wib,
    level_from_score,
)


class _FakeMappings:
    def all(self):
        return []


class _FakeResult:
    def mappings(self):
        return _FakeMappings()


class _FakeSession:
    def __init__(self) -> None:
        self.sql = ""
        self.params = {}

    def execute(self, statement, params):
        self.sql = str(statement)
        self.params = params
        return _FakeResult()


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


if __name__ == "__main__":
    unittest.main()
