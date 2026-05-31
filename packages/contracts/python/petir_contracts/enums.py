"""Shared enumerations for the PetirDashboard wire contract.

Mirrors schema/enums.json. This is the single source of truth in Python form,
imported by BOTH the edge sync worker and the server ingest layer. Neither side
imports the other; both import petir_contracts.
"""
from __future__ import annotations

from enum import Enum


class TableName(str, Enum):
    weather_samples = "weather_samples"
    weather_minute_summary = "weather_minute_summary"
    lightning_events = "lightning_events"
    lightning_minute_summary = "lightning_minute_summary"
    weather_quality_events = "weather_quality_events"
    system_events = "system_events"


class CursorStrategy(str, Enum):
    """append -> monotonic edge id (event tables).

    summary -> monotonic change_seq (late-updated minute tables).
    """

    append = "append"
    summary = "summary"


class WeatherStatus(str, Enum):
    ok = "ok"
    warn = "warn"
    degraded = "degraded"
    invalid = "invalid"
    no_data = "no_data"


class LightningStatus(str, Enum):
    quiet = "quiet"
    noise = "noise"
    disturber = "disturber"
    activity = "activity"
    saturated = "saturated"
    no_data = "no_data"


class LightningEventType(str, Enum):
    lightning = "lightning"
    disturber = "disturber"
    noise = "noise"


class QualityStatus(str, Enum):
    ok = "ok"
    warn = "warn"
    invalid = "invalid"


class SystemLevel(str, Enum):
    debug = "debug"
    info = "info"
    warn = "warn"
    error = "error"
    critical = "critical"


class IngestStatus(str, Enum):
    accepted = "accepted"
    partial = "partial"
    rejected = "rejected"


# Cursor strategy per table (matches edge/sync_worker/tables.py PRIORITY/CONFIG).
TABLE_STRATEGY: dict[TableName, CursorStrategy] = {
    TableName.system_events: CursorStrategy.append,
    TableName.weather_minute_summary: CursorStrategy.summary,
    TableName.lightning_minute_summary: CursorStrategy.summary,
    TableName.weather_quality_events: CursorStrategy.append,
    TableName.lightning_events: CursorStrategy.append,
    TableName.weather_samples: CursorStrategy.append,
}
