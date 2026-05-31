from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WeatherSample(Base):
    __tablename__ = "weather_samples"

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
    temperature_c: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    humidity_pct: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    pressure_hpa: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    illuminance_lux: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    rain_mm: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    wind_speed_ms: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    wind_dir_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wind_dir_deg: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    raw_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    edge_ingest_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "node_id",
            "db_epoch",
            "edge_id",
            name="uq_weather_samples_node_id_db_epoch_edge_id",
        ),
        Index(
            "ix_weather_samples_node_id_ts_pi_utc",
            "node_id",
            text("ts_pi_utc DESC"),
        ),
        Index("ix_weather_samples_ts_pi_utc", text("ts_pi_utc DESC")),
    )


class WeatherMinuteSummary(Base):
    __tablename__ = "weather_minute_summary"

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
    sample_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metric_sample_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    valid_sample_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    warn_sample_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    invalid_sample_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    degraded: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    temperature_avg: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    temperature_min: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    temperature_max: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    humidity_avg: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    humidity_min: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    humidity_max: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    pressure_avg: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    pressure_min: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    pressure_max: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    illuminance_avg: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    illuminance_min: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    illuminance_max: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    rain_max: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    wind_speed_avg: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    wind_speed_max: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    latest_wind_dir_deg: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    last_sample_ts_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "node_id",
            "minute_utc",
            "source",
            "device",
            name="uq_weather_minute_summary_node_id_minute_utc_source_device",
        ),
        Index("ix_weather_minute_summary_minute_utc", text("minute_utc DESC")),
    )
