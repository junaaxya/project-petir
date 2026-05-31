"""Pydantic row models for the PetirDashboard wire contract.

Mirrors schema/rows/*.json. Used by the server to validate inbound rows and by
the edge to shape outbound rows. Field sets match the edge SQLite tables exactly.
"""
from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict

from .enums import (
    LightningEventType,
    LightningStatus,
    QualityStatus,
    SystemLevel,
    WeatherStatus,
)

JsonValue = Union[dict, str, None]


class _Row(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WeatherSampleRow(_Row):
    edge_id: int
    ts_pi_utc: str
    source: Optional[str] = None
    device: Optional[str] = None
    sensor: Optional[str] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    illuminance_lux: Optional[float] = None
    rain_mm: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_dir_code: Optional[int] = None
    wind_dir_deg: Optional[float] = None
    raw_json: JsonValue = None
    ingest_run_id: Optional[int] = None
    created_at_utc: str


class WeatherMinuteSummaryRow(_Row):
    change_seq: int
    minute_utc: str
    source: str
    device: str
    sample_count: Optional[int] = None
    metric_sample_count: Optional[int] = None
    valid_sample_count: Optional[int] = None
    warn_sample_count: Optional[int] = None
    invalid_sample_count: Optional[int] = None
    status: Optional[WeatherStatus] = None
    degraded: Optional[bool] = None
    temperature_avg: Optional[float] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    humidity_avg: Optional[float] = None
    humidity_min: Optional[float] = None
    humidity_max: Optional[float] = None
    pressure_avg: Optional[float] = None
    pressure_min: Optional[float] = None
    pressure_max: Optional[float] = None
    illuminance_avg: Optional[float] = None
    illuminance_min: Optional[float] = None
    illuminance_max: Optional[float] = None
    rain_max: Optional[float] = None
    wind_speed_avg: Optional[float] = None
    wind_speed_max: Optional[float] = None
    latest_wind_dir_deg: Optional[float] = None
    last_sample_ts_utc: Optional[str] = None
    updated_at_utc: str


class LightningEventRow(_Row):
    edge_id: int
    ts_pi_utc: str
    source: Optional[str] = None
    device: Optional[str] = None
    sensor: Optional[str] = None
    event_type: Optional[LightningEventType] = None
    distance_km: Optional[float] = None
    energy_raw: Optional[int] = None
    noise_level: Optional[int] = None
    irq_source: Optional[int] = None
    raw_line: Optional[str] = None
    ingest_run_id: Optional[int] = None
    created_at_utc: str


class LightningMinuteSummaryRow(_Row):
    change_seq: int
    minute_utc: str
    source: str
    device: str
    lightning_count: Optional[int] = None
    disturber_count: Optional[int] = None
    noise_window_count: Optional[int] = None
    noise_event_count: Optional[int] = None
    status: Optional[LightningStatus] = None
    last_event_ts_utc: Optional[str] = None
    last_distance_km: Optional[float] = None
    max_energy_raw: Optional[int] = None
    updated_at_utc: str


class WeatherQualityEventRow(_Row):
    edge_id: int
    ts_pi_utc: Optional[str] = None
    minute_utc: Optional[str] = None
    sample_ts_utc: Optional[str] = None
    source: Optional[str] = None
    device: Optional[str] = None
    quality_status: Optional[QualityStatus] = None
    reason_codes: Union[str, list, None] = None
    message: Optional[str] = None
    details_json: JsonValue = None
    created_at_utc: str


class SystemEventRow(_Row):
    edge_id: int
    ts_pi_utc: str
    source: Optional[str] = None
    level: Optional[SystemLevel] = None
    event_type: Optional[str] = None
    message: Optional[str] = None
    details_json: JsonValue = None
    created_at_utc: str


ROW_MODELS = {
    "weather_samples": WeatherSampleRow,
    "weather_minute_summary": WeatherMinuteSummaryRow,
    "lightning_events": LightningEventRow,
    "lightning_minute_summary": LightningMinuteSummaryRow,
    "weather_quality_events": WeatherQualityEventRow,
    "system_events": SystemEventRow,
}
