"""add retention policy and AI hooks infrastructure

Revision ID: 0003_retention_ai_hooks
Revises: 0002_token_rotation
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retention_policies",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.Text, nullable=False, unique=True),
        sa.Column("retain_days", sa.Integer, nullable=False, server_default="90"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "last_pruned_utc",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("rows_pruned_last", sa.Integer, nullable=True),
    )

    op.execute("""
        INSERT INTO retention_policies (table_name, retain_days) VALUES
            ('weather_samples', 90),
            ('weather_minute_summary', 365),
            ('lightning_events', 90),
            ('lightning_minute_summary', 365),
            ('weather_quality_events', 60),
            ('system_events', 30)
        ON CONFLICT (table_name) DO NOTHING
    """)

    op.create_table(
        "ai_hook_results",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("hook_type", sa.Text, nullable=False),
        sa.Column("node_id", sa.Text, sa.ForeignKey("edge_nodes.node_id"), nullable=False),
        sa.Column("computed_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("window_start_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Double, nullable=True),
        sa.Column("label", sa.Text, nullable=True),
        sa.Column("details_json", sa.dialects.postgresql.JSONB, nullable=True),
    )
    op.create_index(
        "ix_ai_hook_results_hook_type_node_id",
        "ai_hook_results",
        ["hook_type", "node_id", sa.text("computed_at_utc DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_hook_results_hook_type_node_id")
    op.drop_table("ai_hook_results")
    op.drop_table("retention_policies")
