"""Sync batch envelope + server response models.

Mirrors schema/envelope.json. The envelope is the POST /api/ingest/sync-batch
request body; SyncBatchResponse is the server reply carrying the authoritative
accepted_cursor that the edge must persist.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Optional
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from .enums import CursorStrategy, IngestStatus, TableName

NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]


def _datetime_input(value: Any) -> Any:
    if value is not None and not isinstance(value, (str, datetime)):
        raise ValueError("datetime must be an RFC 3339 string")
    return value


JsonDateTime = Annotated[datetime, BeforeValidator(_datetime_input)]


class Cursor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: Optional[CursorStrategy] = None
    last_edge_id: Optional[NonNegativeInt] = None
    last_change_seq: Optional[NonNegativeInt] = None


class RunMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_at_utc: Optional[JsonDateTime] = None
    duration_ms: Optional[NonNegativeInt] = None
    sequence: Optional[PositiveInt] = None


class SyncBatchEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    node_id: str = Field(min_length=1)
    db_epoch: UUID
    run_id: UUID
    run: Optional[RunMeta] = None
    table: TableName
    cursor: Cursor
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=1000)


class RejectedRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: NonNegativeInt
    reason: str
    field: Optional[str] = None


class SyncBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    table: TableName
    status: IngestStatus
    accepted: NonNegativeInt
    rejected: list[RejectedRow] = Field(default_factory=list)
    accepted_cursor: Cursor
    server_contract_version: str
