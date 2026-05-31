from __future__ import annotations

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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    retain_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("90")
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    last_pruned_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rows_pruned_last: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class AiHookResult(Base):
    __tablename__ = "ai_hook_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    hook_type: Mapped[str] = mapped_column(Text, nullable=False)
    node_id: Mapped[str] = mapped_column(
        Text, ForeignKey("edge_nodes.node_id"), nullable=False
    )
    computed_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    window_start_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    window_end_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    score: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index(
            "ix_ai_hook_results_hook_type_node_id",
            "hook_type",
            "node_id",
            text("computed_at_utc DESC"),
        ),
    )
