from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WeatherQualityEvent(Base):
    __tablename__ = "weather_quality_events"

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
    ts_pi_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    minute_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sample_ts_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "node_id",
            "db_epoch",
            "edge_id",
            name="uq_weather_quality_events_node_id_db_epoch_edge_id",
        ),
        Index("ix_weather_quality_events_minute_utc", text("minute_utc DESC")),
    )


class SystemEvent(Base):
    __tablename__ = "system_events"

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
    level: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "node_id",
            "db_epoch",
            "edge_id",
            name="uq_system_events_node_id_db_epoch_edge_id",
        ),
        Index(
            "ix_system_events_node_id_ts_pi_utc",
            "node_id",
            text("ts_pi_utc DESC"),
        ),
        Index(
            "ix_system_events_level_ts_pi_utc",
            "level",
            text("ts_pi_utc DESC"),
        ),
    )
