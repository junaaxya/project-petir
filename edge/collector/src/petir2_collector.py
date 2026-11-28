"""Local Petir 2 edge SQLite store; never sends data to the network."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


WEATHER_SOURCE = "weather_station"
WEATHER_DEVICE = "ws3_sen0390_bridge"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def minute_utc(timestamp: str) -> str:
    value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return value.astimezone(timezone.utc).replace(second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _avg(previous_average: Optional[float], previous_count: int, value: Optional[float]) -> Optional[float]:
    if value is None:
        return previous_average
    if previous_average is None or previous_count <= 0:
        return float(value)
    return ((previous_average * previous_count) + float(value)) / (previous_count + 1)


def _min(previous: Optional[float], value: Optional[float]) -> Optional[float]:
    if value is None:
        return previous
    return float(value) if previous is None else min(previous, float(value))


def _max(previous: Optional[float], value: Optional[float]) -> Optional[float]:
    if value is None:
        return previous
    return float(value) if previous is None else max(previous, float(value))


class EdgeStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.conn: sqlite3.Connection | None = None
        self.db_epoch = ""

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()
        row = self.conn.execute("SELECT value FROM meta WHERE key='db_epoch'").fetchone()
        if row is None:
            self.db_epoch = str(uuid.uuid4())
            self.conn.execute("INSERT INTO meta(key,value) VALUES('db_epoch',?)", (self.db_epoch,))
            self.conn.commit()
        else:
            self.db_epoch = row[0]

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def _create_schema(self) -> None:
        assert self.conn is not None
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sync_state (
              table_name TEXT PRIMARY KEY, last_edge_id INTEGER, last_change_seq INTEGER,
              last_acked_at TEXT, rows_sent INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS change_seq_counter (table_name TEXT PRIMARY KEY, value INTEGER NOT NULL DEFAULT 0);
            INSERT OR IGNORE INTO change_seq_counter(table_name,value) VALUES
              ('weather_minute_summary',0),('lightning_minute_summary',0);

            CREATE TABLE IF NOT EXISTS weather_samples (
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts_pi_utc TEXT NOT NULL,
              source TEXT, device TEXT, sensor TEXT,
              temperature_c REAL, humidity_pct REAL, pressure_hpa REAL, illuminance_lux REAL,
              rain_mm REAL, wind_speed_ms REAL, wind_dir_code INTEGER, wind_dir_deg REAL,
              raw_json TEXT, ingest_run_id INTEGER, created_at_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS weather_samples_ts_idx ON weather_samples(ts_pi_utc);

            CREATE TABLE IF NOT EXISTS weather_minute_summary (
              minute_utc TEXT NOT NULL, source TEXT NOT NULL, device TEXT NOT NULL,
              sample_count INTEGER, metric_sample_count INTEGER, valid_sample_count INTEGER,
              warn_sample_count INTEGER, invalid_sample_count INTEGER, status TEXT, degraded INTEGER,
              temperature_avg REAL, temperature_min REAL, temperature_max REAL,
              humidity_avg REAL, humidity_min REAL, humidity_max REAL,
              pressure_avg REAL, pressure_min REAL, pressure_max REAL,
              illuminance_avg REAL, illuminance_min REAL, illuminance_max REAL,
              rain_max REAL, wind_speed_avg REAL, wind_speed_max REAL, latest_wind_dir_deg REAL,
              last_sample_ts_utc TEXT, updated_at_utc TEXT NOT NULL, change_seq INTEGER,
              PRIMARY KEY(minute_utc,source,device)
            );
            CREATE TABLE IF NOT EXISTS lightning_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts_pi_utc TEXT NOT NULL,
              source TEXT, device TEXT, sensor TEXT, event_type TEXT, distance_km REAL,
              energy_raw INTEGER, noise_level INTEGER, irq_source INTEGER, raw_line TEXT,
              ingest_run_id INTEGER, created_at_utc TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lightning_minute_summary (
              minute_utc TEXT NOT NULL, source TEXT NOT NULL, device TEXT NOT NULL,
              lightning_count INTEGER, disturber_count INTEGER, noise_window_count INTEGER,
              noise_event_count INTEGER, status TEXT, last_event_ts_utc TEXT,
              last_distance_km REAL, max_energy_raw INTEGER, updated_at_utc TEXT NOT NULL,
              change_seq INTEGER, PRIMARY KEY(minute_utc,source,device)
            );
            -- Local-only health state; never read by the production sync worker.
            CREATE TABLE IF NOT EXISTS lightning_sensor_health (
              id INTEGER PRIMARY KEY CHECK(id=1), state TEXT NOT NULL,
              last_heartbeat_utc TEXT, last_status_utc TEXT, details_json TEXT,
              updated_at_utc TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS weather_quality_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts_pi_utc TEXT, minute_utc TEXT,
              sample_ts_utc TEXT, source TEXT, device TEXT, quality_status TEXT,
              reason_codes TEXT, message TEXT, details_json TEXT, created_at_utc TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS system_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts_pi_utc TEXT NOT NULL, source TEXT,
              level TEXT, event_type TEXT, message TEXT, details_json TEXT, created_at_utc TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sync_runs (
              run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
              status TEXT, tables_count INTEGER DEFAULT 0, rows_sent INTEGER DEFAULT 0,
              rows_rejected INTEGER DEFAULT 0, exit_code INTEGER, error_detail TEXT
            );
            -- Local-only metadata; intentionally outside the ingest contract.
            CREATE TABLE IF NOT EXISTS station_location_metadata (
              id INTEGER PRIMARY KEY CHECK(id=1), latitude REAL, longitude REAL,
              source TEXT NOT NULL, accuracy_m REAL, updated_at_utc TEXT NOT NULL, notes TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_wms_change_seq ON weather_minute_summary(change_seq);
            CREATE INDEX IF NOT EXISTS idx_lms_change_seq ON lightning_minute_summary(change_seq);

            CREATE TRIGGER IF NOT EXISTS wms_change_seq_ins AFTER INSERT ON weather_minute_summary
            BEGIN
              UPDATE change_seq_counter SET value=value+1 WHERE table_name='weather_minute_summary';
              UPDATE weather_minute_summary SET change_seq=(SELECT value FROM change_seq_counter WHERE table_name='weather_minute_summary') WHERE rowid=NEW.rowid;
            END;
            CREATE TRIGGER IF NOT EXISTS wms_change_seq_upd AFTER UPDATE ON weather_minute_summary
            WHEN NEW.change_seq IS OLD.change_seq
            BEGIN
              UPDATE change_seq_counter SET value=value+1 WHERE table_name='weather_minute_summary';
              UPDATE weather_minute_summary SET change_seq=(SELECT value FROM change_seq_counter WHERE table_name='weather_minute_summary') WHERE rowid=NEW.rowid;
            END;
            CREATE TRIGGER IF NOT EXISTS lms_change_seq_ins AFTER INSERT ON lightning_minute_summary
            BEGIN
              UPDATE change_seq_counter SET value=value+1 WHERE table_name='lightning_minute_summary';
              UPDATE lightning_minute_summary SET change_seq=(SELECT value FROM change_seq_counter WHERE table_name='lightning_minute_summary') WHERE rowid=NEW.rowid;
            END;
            CREATE TRIGGER IF NOT EXISTS lms_change_seq_upd AFTER UPDATE ON lightning_minute_summary
            WHEN NEW.change_seq IS OLD.change_seq
            BEGIN
              UPDATE change_seq_counter SET value=value+1 WHERE table_name='lightning_minute_summary';
              UPDATE lightning_minute_summary SET change_seq=(SELECT value FROM change_seq_counter WHERE table_name='lightning_minute_summary') WHERE rowid=NEW.rowid;
            END;
            """
        )
        self.conn.commit()

    def record_system_event(self, level: str, event_type: str, message: str, details: dict[str, Any]) -> int:
        assert self.conn is not None
        now = utc_now_iso()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO system_events(ts_pi_utc,source,level,event_type,message,details_json,created_at_utc) VALUES(?,?,?,?,?,?,?)",
                (now, "petir2_collector", level, event_type, message, _json(details), now),
            )
        return int(cur.lastrowid)

    def record_quality_event(self, *, ts_pi_utc: Optional[str], quality_status: str, reason_codes: list[str], message: str, details: dict[str, Any]) -> int:
        assert self.conn is not None
        now = utc_now_iso()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO weather_quality_events(ts_pi_utc,minute_utc,sample_ts_utc,source,device,quality_status,reason_codes,message,details_json,created_at_utc) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (ts_pi_utc, minute_utc(ts_pi_utc) if ts_pi_utc else None, ts_pi_utc, WEATHER_SOURCE, WEATHER_DEVICE, quality_status, _json(reason_codes), message, _json(details), now),
            )
        return int(cur.lastrowid)

    def insert_weather_sample(self, ts_pi_utc: str, payload: dict[str, Any]) -> int:
        assert self.conn is not None
        now = utc_now_iso()
        temp = payload.get("temperature_c")
        humidity = payload.get("humidity_pct")
        pressure = payload.get("pressure_hpa")
        lux = payload.get("illuminance_lux")
        rain = payload.get("rain_1m_mm")
        wind = payload.get("wind_speed_ms")
        direction_code = payload.get("wind_dir_code")
        direction_deg = payload.get("wind_dir_deg")
        metric_values = [temp, humidity, pressure, lux, rain, wind]
        metric_count = sum(value is not None for value in metric_values)
        status = "ok" if metric_count >= 3 else "warn"
        minute = minute_utc(ts_pi_utc)

        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO weather_samples(ts_pi_utc,source,device,sensor,temperature_c,humidity_pct,pressure_hpa,illuminance_lux,rain_mm,wind_speed_ms,wind_dir_code,wind_dir_deg,raw_json,ingest_run_id,created_at_utc) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ts_pi_utc, WEATHER_SOURCE, WEATHER_DEVICE, "ws3+sen0390", temp, humidity, pressure, lux, rain, wind, direction_code, direction_deg, _json(payload), None, now),
            )
            sample_id = int(cur.lastrowid)
            existing = self.conn.execute(
                "SELECT * FROM weather_minute_summary WHERE minute_utc=? AND source=? AND device=?",
                (minute, WEATHER_SOURCE, WEATHER_DEVICE),
            ).fetchone()
            if existing is None:
                self.conn.execute(
                    "INSERT INTO weather_minute_summary(minute_utc,source,device,sample_count,metric_sample_count,valid_sample_count,warn_sample_count,invalid_sample_count,status,degraded,temperature_avg,temperature_min,temperature_max,humidity_avg,humidity_min,humidity_max,pressure_avg,pressure_min,pressure_max,illuminance_avg,illuminance_min,illuminance_max,rain_max,wind_speed_avg,wind_speed_max,latest_wind_dir_deg,last_sample_ts_utc,updated_at_utc) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (minute, WEATHER_SOURCE, WEATHER_DEVICE, 1, metric_count, 1 if status == "ok" else 0, 1 if status == "warn" else 0, 0, status, 1 if status == "warn" else 0,
                     temp, temp, temp, humidity, humidity, humidity, pressure, pressure, pressure, lux, lux, lux, rain, wind, wind, direction_deg, ts_pi_utc, now),
                )
            else:
                prior_samples = int(existing["sample_count"] or 0)
                next_status = "warn" if existing["status"] == "warn" or status == "warn" else "ok"
                self.conn.execute(
                    "UPDATE weather_minute_summary SET sample_count=?,metric_sample_count=?,valid_sample_count=?,warn_sample_count=?,status=?,degraded=?,temperature_avg=?,temperature_min=?,temperature_max=?,humidity_avg=?,humidity_min=?,humidity_max=?,pressure_avg=?,pressure_min=?,pressure_max=?,illuminance_avg=?,illuminance_min=?,illuminance_max=?,rain_max=?,wind_speed_avg=?,wind_speed_max=?,latest_wind_dir_deg=?,last_sample_ts_utc=?,updated_at_utc=? WHERE minute_utc=? AND source=? AND device=?",
                    (prior_samples + 1, int(existing["metric_sample_count"] or 0) + metric_count,
                     int(existing["valid_sample_count"] or 0) + (1 if status == "ok" else 0),
                     int(existing["warn_sample_count"] or 0) + (1 if status == "warn" else 0), next_status, 1 if next_status == "warn" else 0,
                     _avg(existing["temperature_avg"], prior_samples, temp), _min(existing["temperature_min"], temp), _max(existing["temperature_max"], temp),
                     _avg(existing["humidity_avg"], prior_samples, humidity), _min(existing["humidity_min"], humidity), _max(existing["humidity_max"], humidity),
                     _avg(existing["pressure_avg"], prior_samples, pressure), _min(existing["pressure_min"], pressure), _max(existing["pressure_max"], pressure),
                     _avg(existing["illuminance_avg"], prior_samples, lux), _min(existing["illuminance_min"], lux), _max(existing["illuminance_max"], lux),
                     _max(existing["rain_max"], rain), _avg(existing["wind_speed_avg"], prior_samples, wind), _max(existing["wind_speed_max"], wind),
                     direction_deg if direction_deg is not None else existing["latest_wind_dir_deg"],
                     ts_pi_utc, now, minute, WEATHER_SOURCE, WEATHER_DEVICE),
                )
        return sample_id

    def insert_lightning_event(self, ts_pi_utc: str, payload: dict[str, Any]) -> int:
        """Append a real AS3935 event and update its minute aggregate."""
        assert self.conn is not None
        event_type = str(payload["event_type"])
        if event_type not in {"lightning", "noise", "disturber"}:
            raise ValueError("unsupported lightning event type")
        now = utc_now_iso()
        minute = minute_utc(ts_pi_utc)
        source, device, sensor = "as3935", "sen0290_uno", "AS3935"
        distance = payload.get("distance_km")
        energy = payload.get("energy_raw")
        irq_source = payload.get("irq_source")
        raw_line = payload.get("raw_line")
        noise_window_count = int(payload.get("noise_window_count") or 0)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO lightning_events(ts_pi_utc,source,device,sensor,event_type,distance_km,energy_raw,noise_level,irq_source,raw_line,ingest_run_id,created_at_utc) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (ts_pi_utc, source, device, sensor, event_type, distance, energy, None, irq_source, raw_line, None, now),
            )
            existing = self.conn.execute(
                "SELECT * FROM lightning_minute_summary WHERE minute_utc=? AND source=? AND device=?",
                (minute, source, device),
            ).fetchone()
            lightning = 1 if event_type == "lightning" else 0
            disturber = 1 if event_type == "disturber" else 0
            noise = 1 if event_type == "noise" else 0
            status = "activity" if lightning else "disturber" if disturber else "noise"
            if existing is None:
                self.conn.execute(
                    "INSERT INTO lightning_minute_summary(minute_utc,source,device,lightning_count,disturber_count,noise_window_count,noise_event_count,status,last_event_ts_utc,last_distance_km,max_energy_raw,updated_at_utc) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (minute, source, device, lightning, disturber, noise_window_count, noise, status, ts_pi_utc if lightning else None, distance if lightning else None, energy if lightning else None, now),
                )
            else:
                next_lightning = int(existing["lightning_count"] or 0) + lightning
                next_disturber = int(existing["disturber_count"] or 0) + disturber
                next_noise = int(existing["noise_event_count"] or 0) + noise
                next_status = "activity" if next_lightning else "disturber" if next_disturber else "noise"
                self.conn.execute(
                    "UPDATE lightning_minute_summary SET lightning_count=?,disturber_count=?,noise_window_count=?,noise_event_count=?,status=?,last_event_ts_utc=?,last_distance_km=?,max_energy_raw=?,updated_at_utc=? WHERE minute_utc=? AND source=? AND device=?",
                    (next_lightning, next_disturber, max(int(existing["noise_window_count"] or 0), noise_window_count), next_noise, next_status,
                     ts_pi_utc if lightning else existing["last_event_ts_utc"],
                     distance if lightning else existing["last_distance_km"],
                     _max(existing["max_energy_raw"], energy) if lightning else existing["max_energy_raw"],
                     now, minute, source, device),
                )
        return int(cur.lastrowid)

    def record_lightning_no_data(self, ts_pi_utc: str) -> None:
        """Represent an unobserved minute without falsely calling it quiet."""
        assert self.conn is not None
        now = utc_now_iso()
        minute = minute_utc(ts_pi_utc)
        source, device = "as3935", "sen0290_uno"
        with self.conn:
            existing = self.conn.execute(
                "SELECT 1 FROM lightning_minute_summary WHERE minute_utc=? AND source=? AND device=?",
                (minute, source, device),
            ).fetchone()
            if existing is None:
                self.conn.execute(
                    "INSERT INTO lightning_minute_summary(minute_utc,source,device,lightning_count,disturber_count,noise_window_count,noise_event_count,status,last_event_ts_utc,last_distance_km,max_energy_raw,updated_at_utc) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (minute, source, device, 0, 0, 0, 0, "no_data", None, None, None, now),
                )

    def record_lightning_quiet(self, ts_pi_utc: str) -> None:
        """Record an alive-but-quiet minute without inventing distance or events."""
        assert self.conn is not None
        now = utc_now_iso()
        minute = minute_utc(ts_pi_utc)
        source, device = "as3935", "sen0290_uno"
        with self.conn:
            existing = self.conn.execute(
                "SELECT 1 FROM lightning_minute_summary WHERE minute_utc=? AND source=? AND device=?",
                (minute, source, device),
            ).fetchone()
            if existing is None:
                self.conn.execute(
                    "INSERT INTO lightning_minute_summary(minute_utc,source,device,lightning_count,disturber_count,noise_window_count,noise_event_count,status,last_event_ts_utc,last_distance_km,max_energy_raw,updated_at_utc) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (minute, source, device, 0, 0, 0, 0, "quiet", None, None, None, now),
                )

    def record_lightning_health(self, state: str, ts_pi_utc: str, details: dict[str, Any], *, heartbeat: bool = False) -> None:
        """Persist local health only; production contracts exclude this table."""
        assert self.conn is not None
        now = utc_now_iso()
        with self.conn:
            self.conn.execute(
                "INSERT INTO lightning_sensor_health(id,state,last_heartbeat_utc,last_status_utc,details_json,updated_at_utc) VALUES(1,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET state=excluded.state,last_heartbeat_utc=CASE WHEN ? THEN excluded.last_heartbeat_utc ELSE lightning_sensor_health.last_heartbeat_utc END,last_status_utc=excluded.last_status_utc,details_json=excluded.details_json,updated_at_utc=excluded.updated_at_utc",
                (state, ts_pi_utc if heartbeat else None, ts_pi_utc, _json(details), now, 1 if heartbeat else 0),
            )

    def integrity_check(self) -> str:
        assert self.conn is not None
        return str(self.conn.execute("PRAGMA integrity_check").fetchone()[0])
