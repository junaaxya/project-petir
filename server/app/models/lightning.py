from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class LightningEvent(Base):
    __tablename__ = "lightning_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(
        Text, ForeignKey("edge_nodes.node_id"), nullable=False
    )
    db_epoch: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    synced_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    ingest_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sync_runs.run_id"), nullable=True
    )

    edge_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ts_pi_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sensor: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    distance_km: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    energy_raw: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    noise_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    irq_source: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    raw_line: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edge_ingest_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "node_id",
            "db_epoch",
            "edge_id",
            name="uq_lightning_events_node_id_db_epoch_edge_id",
        ),
        Index(
            "ix_lightning_events_node_id_ts_pi_utc",
            "node_id",
            text("ts_pi_utc DESC"),
        ),
    )


class LightningMinuteSummary(Base):
    __tablename__ = "lightning_minute_summary"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(
        Text, ForeignKey("edge_nodes.node_id"), nullable=False
    )
    db_epoch: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    synced_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    ingest_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sync_runs.run_id"), nullable=True
    )

    change_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    minute_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    device: Mapped[str] = mapped_column(Text, nullable=False)
    lightning_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    disturber_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    noise_window_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    noise_event_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_event_ts_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_distance_km: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    max_energy_raw: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "node_id",
            "minute_utc",
            "source",
            "device",
            name="uq_lightning_minute_summary_node_id_minute_utc_source_device",
        ),
        Index("ix_lightning_minute_summary_minute_utc", text("minute_utc DESC")),
    )
