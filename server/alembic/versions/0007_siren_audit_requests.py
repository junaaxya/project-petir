"""add siren audit request persistence

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "siren_audit_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("node_id", sa.Text(), sa.ForeignKey("edge_nodes.node_id"), nullable=False),
        sa.Column("requested_by", sa.Text(), nullable=False),
        sa.Column("requested_role", sa.Text(), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("duration_sec", sa.Float(), nullable=False),
        sa.Column("repeats", sa.Integer(), nullable=False),
        sa.Column("gap_sec", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("result_message", sa.Text(), nullable=True),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("command_payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("result_details_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_siren_audit_requests_node_id_requested_at",
        "siren_audit_requests",
        ["node_id", sa.text("requested_at DESC")],
    )
    op.create_index(
        "ix_siren_audit_requests_status_requested_at",
        "siren_audit_requests",
        ["status", sa.text("requested_at DESC")],
    )

    op.create_table(
        "siren_audit_status_updates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("siren_audit_requests.request_id"),
            nullable=False,
        ),
        sa.Column("node_id", sa.Text(), sa.ForeignKey("edge_nodes.node_id"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("details_json", postgresql.JSONB(), nullable=True),
        sa.Column("reported_by", sa.Text(), nullable=True),
        sa.Column("reported_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "request_id",
            "status",
            "reported_at_utc",
            name="uq_siren_audit_status_updates_request_status_reported_at",
        ),
    )
    op.create_index(
        "ix_siren_audit_status_updates_request_reported_at",
        "siren_audit_status_updates",
        ["request_id", sa.text("reported_at_utc DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_siren_audit_status_updates_request_reported_at")
    op.drop_table("siren_audit_status_updates")
    op.drop_index("ix_siren_audit_requests_status_requested_at")
    op.drop_index("ix_siren_audit_requests_node_id_requested_at")
    op.drop_table("siren_audit_requests")
