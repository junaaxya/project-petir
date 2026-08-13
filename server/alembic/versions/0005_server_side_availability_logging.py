"""add server-side availability logging state

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("edge_nodes", sa.Column("availability_status", sa.Text(), nullable=True))
    op.add_column(
        "edge_nodes",
        sa.Column("availability_changed_at_utc", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "edge_nodes",
        sa.Column("availability_last_event_type", sa.Text(), nullable=True),
    )
    op.add_column(
        "edge_nodes",
        sa.Column("availability_last_event_at_utc", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("edge_nodes", "availability_last_event_at_utc")
    op.drop_column("edge_nodes", "availability_last_event_type")
    op.drop_column("edge_nodes", "availability_changed_at_utc")
    op.drop_column("edge_nodes", "availability_status")