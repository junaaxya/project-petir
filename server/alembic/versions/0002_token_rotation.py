"""add token rotation columns to edge_nodes

Revision ID: 0002_token_rotation
Revises: 0001_initial
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "edge_nodes",
        sa.Column("previous_token_hash", sa.Text(), nullable=True),
    )
    op.add_column(
        "edge_nodes",
        sa.Column(
            "token_rotated_at_utc",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("edge_nodes", "token_rotated_at_utc")
    op.drop_column("edge_nodes", "previous_token_hash")
