import json
import pathlib
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parents[2] / "collector" / "src"))

from petir2_collector import EdgeStore, utc_now_iso


class EdgeStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = pathlib.Path(self.tmp.name) / "edge.db"
        self.store = EdgeStore(self.db_path)
        self.store.initialize()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_initialization_sets_wal_and_persistent_epoch(self):
        epoch_a = self.store.db_epoch
        self.store.close()
        self.store = EdgeStore(self.db_path)
        self.store.initialize()
        self.assertEqual(self.store.db_epoch, epoch_a)
        conn = sqlite3.connect(self.db_path)
        self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")
        conn.close()

    def test_summary_cursor_indexes_exist_for_sync_worker_queries(self):
        indexes = {row[0] for row in self.store.conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        self.assertIn("idx_wms_change_seq", indexes)
        self.assertIn("idx_lms_change_seq", indexes)

    def test_weather_sample_and_minute_summary_use_rain_max_not_repeated_sum(self):
        timestamp = "2026-11-26T00:00:05.000Z"
        payload = {
            "temperature_c": 26.1,
            "humidity_pct": 70.0,
            "pressure_hpa": 1010.0,
            "illuminance_lux": 42.0,
            "rain_1m_mm": 0.3,
            "wind_speed_ms": 1.2,
            "wind_dir_code": 180,
            "raw_ws3": "A...*00",
        }
        first = self.store.insert_weather_sample(timestamp, payload)
        second = self.store.insert_weather_sample("2026-11-26T00:00:20.000Z", payload)
        self.assertNotEqual(first, second)
        row = self.store.conn.execute(
            "SELECT sample_count, rain_max, temperature_avg, illuminance_avg, change_seq "
            "FROM weather_minute_summary"
        ).fetchone()
        self.assertEqual(row[0], 2)
        self.assertEqual(row[1], 0.3)
        self.assertEqual(row[2], 26.1)
        self.assertEqual(row[3], 42.0)
        self.assertGreaterEqual(row[4], 1)

    def test_wind_direction_is_persisted_and_propagated_to_minute_summary(self):
        moving = {
            "temperature_c": 26.1,
            "humidity_pct": 70.0,
            "pressure_hpa": 1010.0,
            "illuminance_lux": 42.0,
            "rain_1m_mm": 0.0,
            "wind_speed_ms": 1.2,
            "wind_dir_code": 10,
            "wind_dir_deg": 225.0,
        }
        calm = {**moving, "wind_speed_ms": 0.0, "wind_dir_code": None, "wind_dir_deg": None}

        sample_id = self.store.insert_weather_sample("2026-11-26T00:02:05.000Z", moving)
        self.store.insert_weather_sample("2026-11-26T00:02:20.000Z", calm)
        updated_id = self.store.insert_weather_sample(
            "2026-11-26T00:02:40.000Z",
            {**moving, "wind_dir_code": 12, "wind_dir_deg": 270.0},
        )

        samples = self.store.conn.execute(
            "SELECT wind_dir_code, wind_dir_deg FROM weather_samples WHERE id IN (?,?) ORDER BY id",
            (sample_id, updated_id),
        ).fetchall()
        summary = self.store.conn.execute(
            "SELECT latest_wind_dir_deg, change_seq FROM weather_minute_summary "
            "WHERE minute_utc='2026-11-26T00:02:00.000Z'"
        ).fetchone()

        self.assertEqual([tuple(row) for row in samples], [(10, 225.0), (12, 270.0)])
        self.assertEqual(summary[0], 270.0)
        self.assertGreaterEqual(summary[1], 3)

    def test_calm_minute_keeps_direction_null(self):
        self.store.insert_weather_sample(
            "2026-11-26T00:03:05.000Z",
            {
                "temperature_c": 26.1,
                "humidity_pct": 70.0,
                "pressure_hpa": 1010.0,
                "wind_speed_ms": 0.0,
                "wind_dir_code": None,
                "wind_dir_deg": None,
            },
        )
        summary = self.store.conn.execute(
            "SELECT latest_wind_dir_deg FROM weather_minute_summary "
            "WHERE minute_utc='2026-11-26T00:03:00.000Z'"
        ).fetchone()
        self.assertIsNone(summary[0])

    def test_sync_runs_matches_release_worker_columns(self):
        columns = {row[1] for row in self.store.conn.execute("PRAGMA table_info(sync_runs)")}
        self.assertTrue({"run_id", "started_at", "finished_at", "status", "tables_count", "rows_sent", "rows_rejected", "exit_code", "error_detail"}.issubset(columns))

    def test_rain_rolling_window_uses_max_across_tip_counter_reset_and_missing_measurement(self):
        base = {
            "temperature_c": 25.0, "humidity_pct": 70.0, "pressure_hpa": 1000.0,
            "illuminance_lux": 10.0, "wind_speed_ms": 0.0, "wind_dir_code": None,
        }
        self.store.insert_weather_sample("2026-11-26T00:01:01.000Z", {**base, "rain_1m_mm": 0.0, "rain_bucket_count": 10})
        self.store.insert_weather_sample("2026-11-26T00:01:10.000Z", {**base, "rain_1m_mm": 0.3, "rain_bucket_count": 11})
        # A reset counter must not turn rolling rainfall into a negative delta.
        self.store.insert_weather_sample("2026-11-26T00:01:20.000Z", {**base, "rain_1m_mm": 0.3, "rain_bucket_count": 0})
        self.store.insert_weather_sample("2026-11-26T00:01:30.000Z", {**base, "rain_1m_mm": None, "rain_bucket_count": None})
        row = self.store.conn.execute("SELECT rain_max FROM weather_minute_summary WHERE minute_utc='2026-11-26T00:01:00.000Z'").fetchone()
        self.assertEqual(row[0], 0.3)

    def test_quality_and_system_events_are_append_only(self):
        event_id = self.store.record_quality_event(
            ts_pi_utc=utc_now_iso(),
            quality_status="warn",
            reason_codes=["lux_i2c_error"],
            message="SEN0390 returned I2C error",
            details={"raw": "@LUX,ERR,I2C"},
        )
        system_id = self.store.record_system_event("info", "collector_started", "collector started", {})
        self.assertGreater(event_id, 0)
        self.assertGreater(system_id, 0)
        self.assertEqual(
            self.store.conn.execute("SELECT COUNT(*) FROM weather_quality_events").fetchone()[0], 1
        )
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM system_events").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
