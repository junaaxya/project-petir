from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_EDGE_ROOT = Path(__file__).resolve().parent.parent
if str(_EDGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_EDGE_ROOT))


def _create_edge_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_pi_utc TEXT NOT NULL,
            source TEXT, level TEXT, event_type TEXT, message TEXT,
            details_json TEXT,
            created_at_utc TEXT NOT NULL
        );
        CREATE TABLE lightning_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_pi_utc TEXT NOT NULL,
            source TEXT, device TEXT, sensor TEXT, event_type TEXT,
            distance_km REAL, energy_raw INTEGER, noise_level INTEGER,
            irq_source TEXT, raw_line TEXT, ingest_run_id TEXT,
            created_at_utc TEXT NOT NULL
        );
        CREATE TABLE weather_quality_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_pi_utc TEXT, minute_utc TEXT, sample_ts_utc TEXT,
            source TEXT, device TEXT, quality_status TEXT, reason_codes TEXT,
            message TEXT, details_json TEXT, created_at_utc TEXT NOT NULL
        );
        CREATE TABLE weather_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_pi_utc TEXT NOT NULL, source TEXT, device TEXT, sensor TEXT,
            temperature_c REAL, humidity_pct REAL, pressure_hpa REAL,
            illuminance_lux REAL, rain_mm REAL, wind_speed_ms REAL,
            wind_dir_code TEXT, wind_dir_deg REAL, raw_json TEXT,
            ingest_run_id TEXT, created_at_utc TEXT NOT NULL
        );
        CREATE TABLE weather_minute_summary (
            minute_utc TEXT NOT NULL, source TEXT NOT NULL, device TEXT NOT NULL,
            sample_count INTEGER, metric_sample_count INTEGER, valid_sample_count INTEGER,
            warn_sample_count INTEGER, invalid_sample_count INTEGER, status TEXT,
            degraded INTEGER, temperature_avg REAL, temperature_min REAL, temperature_max REAL,
            humidity_avg REAL, humidity_min REAL, humidity_max REAL,
            pressure_avg REAL, pressure_min REAL, pressure_max REAL,
            illuminance_avg REAL, illuminance_min REAL, illuminance_max REAL,
            rain_max REAL, wind_speed_avg REAL, wind_speed_max REAL,
            latest_wind_dir_deg REAL, last_sample_ts_utc TEXT, updated_at_utc TEXT NOT NULL,
            change_seq INTEGER,
            PRIMARY KEY (minute_utc, source, device)
        );
        CREATE TABLE lightning_minute_summary (
            minute_utc TEXT NOT NULL, source TEXT NOT NULL, device TEXT NOT NULL,
            lightning_count INTEGER, disturber_count INTEGER, noise_window_count INTEGER,
            noise_event_count INTEGER, status TEXT, last_event_ts_utc TEXT,
            last_distance_km REAL, max_energy_raw INTEGER, updated_at_utc TEXT NOT NULL,
            change_seq INTEGER,
            PRIMARY KEY (minute_utc, source, device)
        );
        """
    )
    conn.commit()


def _seed(conn: sqlite3.Connection) -> None:
    for i in range(1, 6):
        conn.execute(
            "INSERT INTO system_events(ts_pi_utc, level, event_type, message, created_at_utc) "
            "VALUES(?,?,?,?,?)",
            (f"2026-05-30T03:1{i}:00Z", "info", "boot", f"e{i}", f"2026-05-30T03:1{i}:00Z"),
        )
    for i in range(1, 4):
        conn.execute(
            "INSERT INTO weather_minute_summary(minute_utc, source, device, sample_count, "
            "status, temperature_avg, updated_at_utc, change_seq) VALUES(?,?,?,?,?,?,?,?)",
            (
                f"2026-05-30T03:0{i}:00Z",
                "arduino",
                "weather-01",
                12,
                "ok",
                27.0 + i,
                f"2026-05-30T03:0{i}:30Z",
                i,
            ),
        )
    conn.commit()


@pytest.fixture()
def edge_conn():
    conn = sqlite3.connect(":memory:")
    _create_edge_schema(conn)
    _seed(conn)
    yield conn
    conn.close()


@pytest.fixture()
def empty_edge_conn():
    conn = sqlite3.connect(":memory:")
    _create_edge_schema(conn)
    yield conn
    conn.close()
