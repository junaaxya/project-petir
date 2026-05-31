from __future__ import annotations

from app.models import Base

APPEND_TABLES = (
    "weather_samples",
    "lightning_events",
    "weather_quality_events",
    "system_events",
)
SUMMARY_TABLES = (
    "weather_minute_summary",
    "lightning_minute_summary",
)
DATA_TABLES = APPEND_TABLES + SUMMARY_TABLES
ALL_TABLES = (
    "edge_nodes",
    "sync_runs",
    "sync_cursors",
    "retention_policies",
    "ai_hook_results",
) + DATA_TABLES


def _unique_constraint_columns(table):
    from sqlalchemy import UniqueConstraint

    return [
        {c.name for c in con.columns}
        for con in table.constraints
        if isinstance(con, UniqueConstraint)
    ]


def test_all_eleven_tables_present():
    assert set(Base.metadata.tables) == set(ALL_TABLES)


def test_append_tables_unique_on_node_db_epoch_edge_id():
    expected = {"node_id", "db_epoch", "edge_id"}
    for name in APPEND_TABLES:
        table = Base.metadata.tables[name]
        assert expected in _unique_constraint_columns(table), name


def test_summary_tables_unique_on_node_minute_source_device():
    expected = {"node_id", "minute_utc", "source", "device"}
    for name in SUMMARY_TABLES:
        table = Base.metadata.tables[name]
        assert expected in _unique_constraint_columns(table), name


def test_data_tables_have_common_server_columns():
    required = {"node_id", "db_epoch", "synced_at_utc", "ingest_run_id"}
    for name in DATA_TABLES:
        table = Base.metadata.tables[name]
        assert required.issubset(set(table.columns.keys())), name


def test_sync_cursors_pk_and_cursor_columns():
    table = Base.metadata.tables["sync_cursors"]
    pk_cols = [c.name for c in table.primary_key.columns]
    assert pk_cols == ["node_id", "table_name"]
    assert "last_edge_id" in table.columns
    assert "last_change_seq" in table.columns
