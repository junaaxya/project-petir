from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SirenAuditRequest(Base):
    __tablename__ = "siren_audit_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    node_id: Mapped[str] = mapped_column(Text, ForeignKey("edge_nodes.node_id"), nullable=False)
    requested_by: Mapped[str] = mapped_column(Text, nullable=False)
    requested_role: Mapped[str] = mapped_column(Text, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    duration_sec: Mapped[float] = mapped_column(Float, nullable=False)
    repeats: Mapped[int] = mapped_column(Integer, nullable=False)
    gap_sec: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    result_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cooldown_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status_at_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    command_payload_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    result_details_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "ix_siren_audit_requests_node_id_requested_at",
            "node_id",
            text("requested_at DESC"),
        ),
        Index(
            "ix_siren_audit_requests_status_requested_at",
            "status",
            text("requested_at DESC"),
        ),
    )


class SirenAuditStatusUpdate(Base):
    __tablename__ = "siren_audit_status_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("siren_audit_requests.request_id"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(Text, ForeignKey("edge_nodes.node_id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details_json: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    reported_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reported_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint(
            "request_id",
            "status",
            "reported_at_utc",
            name="uq_siren_audit_status_updates_request_status_reported_at",
        ),
        Index(
            "ix_siren_audit_status_updates_request_reported_at",
            "request_id",
            text("reported_at_utc DESC"),
        ),
    )
