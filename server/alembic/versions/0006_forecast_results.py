"""add forecast results table

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_results",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("forecast_type", sa.Text(), nullable=False),
        sa.Column("node_id", sa.Text(), sa.ForeignKey("edge_nodes.node_id"), nullable=False),
        sa.Column(
            "computed_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("source_window_start_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_window_end_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("target_time_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("horizon_minutes", sa.Integer(), nullable=True),
        sa.Column("score", sa.Double(), nullable=True),
        sa.Column("value_numeric", sa.Double(), nullable=True),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Double(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'ok'")),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("details_json", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_forecast_results_forecast_type_node_id",
        "forecast_results",
        ["forecast_type", "node_id", sa.text("computed_at_utc DESC")],
    )
    op.create_index(
        "ix_forecast_results_node_id",
        "forecast_results",
        ["node_id", sa.text("computed_at_utc DESC")],
    )
    op.create_index(
        "ix_forecast_results_forecast_type",
        "forecast_results",
        ["forecast_type", sa.text("computed_at_utc DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_forecast_results_forecast_type")
    op.drop_index("ix_forecast_results_node_id")
    op.drop_index("ix_forecast_results_forecast_type_node_id")
    op.drop_table("forecast_results")