from __future__ import annotations

import sqlite3

import pytest

from migrations.apply import apply_migration
from migrations.inspect import has_column, inspect, list_triggers


def _make_live_db(path: str, summary_rows: int = 3) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE weather_minute_summary (
            minute_utc TEXT NOT NULL, source TEXT NOT NULL, device TEXT NOT NULL,
            sample_count INTEGER, status TEXT, temperature_avg REAL,
            updated_at_utc TEXT NOT NULL,
            PRIMARY KEY (minute_utc, source, device)
        );
        CREATE TABLE lightning_minute_summary (
            minute_utc TEXT NOT NULL, source TEXT NOT NULL, device TEXT NOT NULL,
            lightning_count INTEGER, status TEXT, updated_at_utc TEXT NOT NULL,
            PRIMARY KEY (minute_utc, source, device)
        );
        CREATE TABLE system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts_pi_utc TEXT NOT NULL,
            level TEXT, created_at_utc TEXT NOT NULL
        );
        """
    )
    for i in range(1, summary_rows + 1):
        conn.execute(
            "INSERT INTO weather_minute_summary(minute_utc, source, device, sample_count, "
            "status, temperature_avg, updated_at_utc) VALUES(?,?,?,?,?,?,?)",
            (f"2026-05-30T03:0{i}:00Z", "arduino", "weather-01", 12, "ok", 27.0 + i,
             f"2026-05-30T03:0{i}:30Z"),
        )
    conn.commit()
    conn.close()


@pytest.fixture()
def live_db(tmp_path):
    path = str(tmp_path / "weather_edge.db")
    _make_live_db(path)
    return path


def test_migration_adds_meta_sync_state_and_triggers(live_db):
    apply_migration(live_db, do_backup=True)
    report = inspect(live_db)
    assert report["meta_exists"]
    assert report["sync_state_exists"]
    triggers = report["triggers"]
    assert "wms_change_seq_ins" in triggers
    assert "wms_change_seq_upd" in triggers
    assert "lms_change_seq_ins" in triggers
    assert "lms_change_seq_upd" in triggers


def test_backup_created(live_db, tmp_path):
    result = apply_migration(live_db, do_backup=True)
    assert result["backup"] is not None
    from pathlib import Path

    assert Path(result["backup"]).exists()


def test_backfill_is_monotonic_and_unique(live_db):
    apply_migration(live_db, do_backup=False)
    conn = sqlite3.connect(live_db)
    seqs = [
        r[0]
        for r in conn.execute(
            "SELECT change_seq FROM weather_minute_summary ORDER BY change_seq"
        ).fetchall()
    ]
    conn.close()
    assert seqs == [1, 2, 3]
    assert len(seqs) == len(set(seqs))
    assert all(s is not None for s in seqs)


def test_rerun_is_idempotent(live_db):
    first = apply_migration(live_db, do_backup=False)
    assert first["added_column"] == ["weather_minute_summary", "lightning_minute_summary"]
    assert first["backfilled"]["weather_minute_summary"] == 3

    second = apply_migration(live_db, do_backup=False)
    assert second["added_column"] == []
    assert second["backfilled"]["weather_minute_summary"] == 0

    conn = sqlite3.connect(live_db)
    count = conn.execute("SELECT count(*) FROM weather_minute_summary").fetchone()[0]
    distinct = conn.execute(
        "SELECT count(DISTINCT change_seq) FROM weather_minute_summary"
    ).fetchone()[0]
    conn.close()
    assert count == 3
    assert distinct == 3


def test_insert_after_migration_gets_change_seq(live_db):
    apply_migration(live_db, do_backup=False)
    conn = sqlite3.connect(live_db)
    conn.execute(
        "INSERT INTO weather_minute_summary(minute_utc, source, device, status, updated_at_utc) "
        "VALUES('2026-05-30T03:10:00Z','arduino','weather-01','ok','2026-05-30T03:10:30Z')"
    )
    conn.commit()
    seq = conn.execute(
        "SELECT change_seq FROM weather_minute_summary WHERE minute_utc='2026-05-30T03:10:00Z'"
    ).fetchone()[0]
    conn.close()
    assert seq == 4


def test_update_to_old_row_bumps_change_seq_above_all(live_db):
    apply_migration(live_db, do_backup=False)
    conn = sqlite3.connect(live_db)
    max_before = conn.execute(
        "SELECT max(change_seq) FROM weather_minute_summary"
    ).fetchone()[0]
    conn.execute(
        "UPDATE weather_minute_summary SET temperature_avg = 99.9 "
        "WHERE minute_utc='2026-05-30T03:01:00Z'"
    )
    conn.commit()
    updated = conn.execute(
        "SELECT change_seq FROM weather_minute_summary WHERE minute_utc='2026-05-30T03:01:00Z'"
    ).fetchone()[0]
    new_max = conn.execute(
        "SELECT max(change_seq) FROM weather_minute_summary"
    ).fetchone()[0]
    conn.close()
    assert updated > max_before
    assert updated == new_max


def test_writer_behavior_unchanged_row_counts(live_db):
    before = inspect(live_db)
    apply_migration(live_db, do_backup=False)
    after = inspect(live_db)
    for table in ("weather_minute_summary", "lightning_minute_summary", "system_events"):
        assert before["tables"][table]["row_count"] == after["tables"][table]["row_count"]


def test_empty_summary_tables_handled(tmp_path):
    path = str(tmp_path / "empty.db")
    _make_live_db(path, summary_rows=0)
    result = apply_migration(path, do_backup=False)
    assert result["backfilled"]["weather_minute_summary"] == 0
    conn = sqlite3.connect(path)
    conn.execute(
        "INSERT INTO weather_minute_summary(minute_utc, source, device, status, updated_at_utc) "
        "VALUES('2026-05-30T03:00:00Z','arduino','weather-01','ok','2026-05-30T03:00:30Z')"
    )
    conn.commit()
    seq = conn.execute("SELECT change_seq FROM weather_minute_summary").fetchone()[0]
    conn.close()
    assert seq == 1
