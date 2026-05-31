"""PetirDashboard shared wire contract (Python).

Single source of truth for the edge<->server sync protocol, imported by both the
edge sync worker and the server ingest layer. Neither imports the other.
"""
from __future__ import annotations

from .enums import (
    CursorStrategy,
    IngestStatus,
    LightningEventType,
    LightningStatus,
    QualityStatus,
    SystemLevel,
    TableName,
    TABLE_STRATEGY,
    WeatherStatus,
)
from .envelope import (
    Cursor,
    RejectedRow,
    RunMeta,
    SyncBatchEnvelope,
    SyncBatchResponse,
)
from .rows import (
    ROW_MODELS,
    LightningEventRow,
    LightningMinuteSummaryRow,
    SystemEventRow,
    WeatherMinuteSummaryRow,
    WeatherQualityEventRow,
    WeatherSampleRow,
)

CONTRACT_VERSION = "2.0.0"

__all__ = [
    "CONTRACT_VERSION",
    "CursorStrategy",
    "IngestStatus",
    "LightningEventType",
    "LightningStatus",
    "QualityStatus",
    "SystemLevel",
    "TableName",
    "TABLE_STRATEGY",
    "WeatherStatus",
    "Cursor",
    "RejectedRow",
    "RunMeta",
    "SyncBatchEnvelope",
    "SyncBatchResponse",
    "ROW_MODELS",
    "LightningEventRow",
    "LightningMinuteSummaryRow",
    "SystemEventRow",
    "WeatherMinuteSummaryRow",
    "WeatherQualityEventRow",
    "WeatherSampleRow",
]
