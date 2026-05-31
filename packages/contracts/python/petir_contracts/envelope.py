"""Sync batch envelope + server response models.

Mirrors schema/envelope.json. The envelope is the POST /api/ingest/sync-batch
request body; SyncBatchResponse is the server reply carrying the authoritative
accepted_cursor that the edge must persist.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import CursorStrategy, IngestStatus, TableName


class Cursor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: Optional[CursorStrategy] = None
    last_edge_id: Optional[int] = None
    last_change_seq: Optional[int] = None


class RunMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_at_utc: Optional[str] = None
    duration_ms: Optional[int] = None
    sequence: Optional[int] = None


class SyncBatchEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    node_id: str = Field(min_length=1)
    db_epoch: str
    run_id: str
    run: Optional[RunMeta] = None
    table: TableName
    cursor: Cursor
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=1000)


class RejectedRow(BaseModel):
    index: int
    reason: str
    field: Optional[str] = None


class SyncBatchResponse(BaseModel):
    run_id: str
    table: TableName
    status: IngestStatus
    accepted: int
    rejected: list[RejectedRow] = []
    accepted_cursor: Cursor
    server_contract_version: str
