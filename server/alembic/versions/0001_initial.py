"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-30 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "edge_nodes",
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("api_token_hash", sa.Text(), nullable=False),
        sa.Column("contract_version", sa.Text(), nullable=True),
        sa.Column("last_seen_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("node_id", name="pk_edge_nodes"),
    )

    op.create_table(
        "sync_runs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "received_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "tables_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "rows_accepted", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "rows_rejected", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["edge_nodes.node_id"],
            name="fk_sync_runs_node_id_edge_nodes",
        ),
        sa.PrimaryKeyConstraint("run_id", name="pk_sync_runs"),
    )
    op.create_index(
        "ix_sync_runs_node_id_received_at_utc",
        "sync_runs",
        ["node_id", sa.text("received_at_utc DESC")],
    )

    op.create_table(
        "sync_cursors",
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("table_name", sa.Text(), nullable=False),
        sa.Column("last_edge_id", sa.BigInteger(), nullable=True),
        sa.Column("last_change_seq", sa.BigInteger(), nullable=True),
        sa.Column("db_epoch", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "rows_total", sa.BigInteger(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("last_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "checkpoint_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["edge_nodes.node_id"],
            name="fk_sync_cursors_node_id_edge_nodes",
        ),
        sa.ForeignKeyConstraint(
            ["last_run_id"],
            ["sync_runs.run_id"],
            name="fk_sync_cursors_last_run_id_sync_runs",
        ),
        sa.PrimaryKeyConstraint("node_id", "table_name", name="pk_sync_cursors"),
    )

    op.create_table(
        "weather_samples",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("db_epoch", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "synced_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("edge_id", sa.BigInteger(), nullable=False),
        sa.Column("ts_pi_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("device", sa.Text(), nullable=True),
        sa.Column("sensor", sa.Text(), nullable=True),
        sa.Column("temperature_c", sa.Double(), nullable=True),
        sa.Column("humidity_pct", sa.Double(), nullable=True),
        sa.Column("pressure_hpa", sa.Double(), nullable=True),
        sa.Column("illuminance_lux", sa.Double(), nullable=True),
        sa.Column("rain_mm", sa.Double(), nullable=True),
        sa.Column("wind_speed_ms", sa.Double(), nullable=True),
        sa.Column("wind_dir_code", sa.Text(), nullable=True),
        sa.Column("wind_dir_deg", sa.Double(), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("edge_ingest_run_id", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["edge_nodes.node_id"],
            name="fk_weather_samples_node_id_edge_nodes",
        ),
        sa.ForeignKeyConstraint(
            ["ingest_run_id"],
            ["sync_runs.run_id"],
            name="fk_weather_samples_ingest_run_id_sync_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_weather_samples"),
        sa.UniqueConstraint(
            "node_id",
            "db_epoch",
            "edge_id",
            name="uq_weather_samples_node_id_db_epoch_edge_id",
        ),
    )
    op.create_index(
        "ix_weather_samples_node_id_ts_pi_utc",
        "weather_samples",
        ["node_id", sa.text("ts_pi_utc DESC")],
    )
    op.create_index(
        "ix_weather_samples_ts_pi_utc",
        "weather_samples",
        [sa.text("ts_pi_utc DESC")],
    )

    op.create_table(
        "weather_minute_summary",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("db_epoch", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "synced_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_seq", sa.BigInteger(), nullable=False),
        sa.Column("minute_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("device", sa.Text(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=True),
        sa.Column("metric_sample_count", sa.Integer(), nullable=True),
        sa.Column("valid_sample_count", sa.Integer(), nullable=True),
        sa.Column("warn_sample_count", sa.Integer(), nullable=True),
        sa.Column("invalid_sample_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("degraded", sa.Boolean(), nullable=True),
        sa.Column("temperature_avg", sa.Double(), nullable=True),
        sa.Column("temperature_min", sa.Double(), nullable=True),
        sa.Column("temperature_max", sa.Double(), nullable=True),
        sa.Column("humidity_avg", sa.Double(), nullable=True),
        sa.Column("humidity_min", sa.Double(), nullable=True),
        sa.Column("humidity_max", sa.Double(), nullable=True),
        sa.Column("pressure_avg", sa.Double(), nullable=True),
        sa.Column("pressure_min", sa.Double(), nullable=True),
        sa.Column("pressure_max", sa.Double(), nullable=True),
        sa.Column("illuminance_avg", sa.Double(), nullable=True),
        sa.Column("illuminance_min", sa.Double(), nullable=True),
        sa.Column("illuminance_max", sa.Double(), nullable=True),
        sa.Column("rain_max", sa.Double(), nullable=True),
        sa.Column("wind_speed_avg", sa.Double(), nullable=True),
        sa.Column("wind_speed_max", sa.Double(), nullable=True),
        sa.Column("latest_wind_dir_deg", sa.Double(), nullable=True),
        sa.Column("last_sample_ts_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["edge_nodes.node_id"],
            name="fk_weather_minute_summary_node_id_edge_nodes",
        ),
        sa.ForeignKeyConstraint(
            ["ingest_run_id"],
            ["sync_runs.run_id"],
            name="fk_weather_minute_summary_ingest_run_id_sync_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_weather_minute_summary"),
        sa.UniqueConstraint(
            "node_id",
            "minute_utc",
            "source",
            "device",
            name="uq_weather_minute_summary_node_id_minute_utc_source_device",
        ),
    )
    op.create_index(
        "ix_weather_minute_summary_minute_utc",
        "weather_minute_summary",
        [sa.text("minute_utc DESC")],
    )

    op.create_table(
        "lightning_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("db_epoch", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "synced_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("edge_id", sa.BigInteger(), nullable=False),
        sa.Column("ts_pi_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("device", sa.Text(), nullable=True),
        sa.Column("sensor", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=True),
        sa.Column("distance_km", sa.Double(), nullable=True),
        sa.Column("energy_raw", sa.BigInteger(), nullable=True),
        sa.Column("noise_level", sa.Integer(), nullable=True),
        sa.Column("irq_source", sa.Text(), nullable=True),
        sa.Column("raw_line", sa.Text(), nullable=True),
        sa.Column("edge_ingest_run_id", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["edge_nodes.node_id"],
            name="fk_lightning_events_node_id_edge_nodes",
        ),
        sa.ForeignKeyConstraint(
            ["ingest_run_id"],
            ["sync_runs.run_id"],
            name="fk_lightning_events_ingest_run_id_sync_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lightning_events"),
        sa.UniqueConstraint(
            "node_id",
            "db_epoch",
            "edge_id",
            name="uq_lightning_events_node_id_db_epoch_edge_id",
        ),
    )
    op.create_index(
        "ix_lightning_events_node_id_ts_pi_utc",
        "lightning_events",
        ["node_id", sa.text("ts_pi_utc DESC")],
    )

    op.create_table(
        "lightning_minute_summary",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("db_epoch", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "synced_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_seq", sa.BigInteger(), nullable=False),
        sa.Column("minute_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("device", sa.Text(), nullable=False),
        sa.Column("lightning_count", sa.Integer(), nullable=True),
        sa.Column("disturber_count", sa.Integer(), nullable=True),
        sa.Column("noise_window_count", sa.Integer(), nullable=True),
        sa.Column("noise_event_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("last_event_ts_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_distance_km", sa.Double(), nullable=True),
        sa.Column("max_energy_raw", sa.BigInteger(), nullable=True),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["edge_nodes.node_id"],
            name="fk_lightning_minute_summary_node_id_edge_nodes",
        ),
        sa.ForeignKeyConstraint(
            ["ingest_run_id"],
            ["sync_runs.run_id"],
            name="fk_lightning_minute_summary_ingest_run_id_sync_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lightning_minute_summary"),
        sa.UniqueConstraint(
            "node_id",
            "minute_utc",
            "source",
            "device",
            name="uq_lightning_minute_summary_node_id_minute_utc_source_device",
        ),
    )
    op.create_index(
        "ix_lightning_minute_summary_minute_utc",
        "lightning_minute_summary",
        [sa.text("minute_utc DESC")],
    )

    op.create_table(
        "weather_quality_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("db_epoch", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "synced_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("edge_id", sa.BigInteger(), nullable=False),
        sa.Column("ts_pi_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("minute_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sample_ts_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("device", sa.Text(), nullable=True),
        sa.Column("quality_status", sa.Text(), nullable=True),
        sa.Column("reason_codes", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["edge_nodes.node_id"],
            name="fk_weather_quality_events_node_id_edge_nodes",
        ),
        sa.ForeignKeyConstraint(
            ["ingest_run_id"],
            ["sync_runs.run_id"],
            name="fk_weather_quality_events_ingest_run_id_sync_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_weather_quality_events"),
        sa.UniqueConstraint(
            "node_id",
            "db_epoch",
            "edge_id",
            name="uq_weather_quality_events_node_id_db_epoch_edge_id",
        ),
    )
    op.create_index(
        "ix_weather_quality_events_minute_utc",
        "weather_quality_events",
        [sa.text("minute_utc DESC")],
    )

    op.create_table(
        "system_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("db_epoch", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "synced_at_utc",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("edge_id", sa.BigInteger(), nullable=False),
        sa.Column("ts_pi_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("level", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["edge_nodes.node_id"],
            name="fk_system_events_node_id_edge_nodes",
        ),
        sa.ForeignKeyConstraint(
            ["ingest_run_id"],
            ["sync_runs.run_id"],
            name="fk_system_events_ingest_run_id_sync_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_system_events"),
        sa.UniqueConstraint(
            "node_id",
            "db_epoch",
            "edge_id",
            name="uq_system_events_node_id_db_epoch_edge_id",
        ),
    )
    op.create_index(
        "ix_system_events_node_id_ts_pi_utc",
        "system_events",
        ["node_id", sa.text("ts_pi_utc DESC")],
    )
    op.create_index(
        "ix_system_events_level_ts_pi_utc",
        "system_events",
        ["level", sa.text("ts_pi_utc DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_system_events_level_ts_pi_utc", table_name="system_events")
    op.drop_index("ix_system_events_node_id_ts_pi_utc", table_name="system_events")
    op.drop_table("system_events")

    op.drop_index(
        "ix_weather_quality_events_minute_utc", table_name="weather_quality_events"
    )
    op.drop_table("weather_quality_events")

    op.drop_index(
        "ix_lightning_minute_summary_minute_utc",
        table_name="lightning_minute_summary",
    )
    op.drop_table("lightning_minute_summary")

    op.drop_index(
        "ix_lightning_events_node_id_ts_pi_utc", table_name="lightning_events"
    )
    op.drop_table("lightning_events")

    op.drop_index(
        "ix_weather_minute_summary_minute_utc", table_name="weather_minute_summary"
    )
    op.drop_table("weather_minute_summary")

    op.drop_index("ix_weather_samples_ts_pi_utc", table_name="weather_samples")
    op.drop_index(
        "ix_weather_samples_node_id_ts_pi_utc", table_name="weather_samples"
    )
    op.drop_table("weather_samples")

    op.drop_table("sync_cursors")

    op.drop_index("ix_sync_runs_node_id_received_at_utc", table_name="sync_runs")
    op.drop_table("sync_runs")

    op.drop_table("edge_nodes")
