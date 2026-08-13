from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Double, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ForecastResult(Base):
    __tablename__ = "forecast_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    forecast_type: Mapped[str] = mapped_column(Text, nullable=False)
    node_id: Mapped[str] = mapped_column(
        Text, ForeignKey("edge_nodes.node_id"), nullable=False
    )
    computed_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    source_window_start_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_window_end_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    target_time_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    horizon_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    value_numeric: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'ok'")
    )
    model_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index(
            "ix_forecast_results_forecast_type_node_id",
            "forecast_type",
            "node_id",
            text("computed_at_utc DESC"),
        ),
        Index(
            "ix_forecast_results_node_id",
            "node_id",
            text("computed_at_utc DESC"),
        ),
        Index(
            "ix_forecast_results_forecast_type",
            "forecast_type",
            text("computed_at_utc DESC"),
        ),
    )