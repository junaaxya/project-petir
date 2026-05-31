"""widen edge passthrough columns to integer (contract v2)

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "weather_samples",
        "wind_dir_code",
        type_=sa.Integer(),
        postgresql_using="wind_dir_code::integer",
    )
    op.alter_column(
        "weather_samples",
        "edge_ingest_run_id",
        type_=sa.BigInteger(),
        postgresql_using="edge_ingest_run_id::bigint",
    )
    op.alter_column(
        "lightning_events",
        "irq_source",
        type_=sa.Integer(),
        postgresql_using="irq_source::integer",
    )
    op.alter_column(
        "lightning_events",
        "edge_ingest_run_id",
        type_=sa.BigInteger(),
        postgresql_using="edge_ingest_run_id::bigint",
    )


def downgrade() -> None:
    op.alter_column(
        "lightning_events",
        "edge_ingest_run_id",
        type_=sa.Text(),
        postgresql_using="edge_ingest_run_id::text",
    )
    op.alter_column(
        "lightning_events",
        "irq_source",
        type_=sa.Text(),
        postgresql_using="irq_source::text",
    )
    op.alter_column(
        "weather_samples",
        "edge_ingest_run_id",
        type_=sa.Text(),
        postgresql_using="edge_ingest_run_id::text",
    )
    op.alter_column(
        "weather_samples",
        "wind_dir_code",
        type_=sa.Text(),
        postgresql_using="wind_dir_code::text",
    )
