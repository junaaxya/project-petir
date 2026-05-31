from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EdgeNode(Base):
    __tablename__ = "edge_nodes"

    node_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    previous_token_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_rotated_at_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    contract_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_seen_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class SyncRun(Base):
    __tablename__ = "sync_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        Text, ForeignKey("edge_nodes.node_id"), nullable=False
    )
    started_at_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    tables_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    rows_accepted: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    rows_rejected: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "ix_sync_runs_node_id_received_at_utc",
            "node_id",
            text("received_at_utc DESC"),
        ),
    )


class SyncCursor(Base):
    __tablename__ = "sync_cursors"

    node_id: Mapped[str] = mapped_column(
        Text, ForeignKey("edge_nodes.node_id"), primary_key=True
    )
    table_name: Mapped[str] = mapped_column(Text, primary_key=True)
    last_edge_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_change_seq: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    db_epoch: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    rows_total: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    last_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sync_runs.run_id"), nullable=True
    )
    checkpoint_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
