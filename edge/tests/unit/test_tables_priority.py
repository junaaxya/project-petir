from __future__ import annotations

from petir_contracts import TableName

from sync_worker.tables import BY_NAME, PRIORITY_ORDER


def test_priority_order_is_complete_and_covers_all_tables():
    names = [t.name for t in PRIORITY_ORDER]
    assert set(names) == {t.value for t in TableName}
    assert len(names) == len(set(names))


def test_system_events_is_highest_priority():
    assert PRIORITY_ORDER[0].name == "system_events"


def test_weather_samples_is_lowest_priority():
    assert PRIORITY_ORDER[-1].name == "weather_samples"


def test_summary_tables_use_change_seq():
    for name in ("weather_minute_summary", "lightning_minute_summary"):
        assert BY_NAME[name].cursor_field == "change_seq"


def test_event_tables_use_edge_id():
    for name in ("system_events", "lightning_events", "weather_quality_events", "weather_samples"):
        assert BY_NAME[name].cursor_field == "edge_id"
