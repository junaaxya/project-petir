from __future__ import annotations

from dataclasses import dataclass

from petir_contracts import CursorStrategy, TableName


@dataclass(frozen=True)
class TableConfig:
    name: str
    strategy: CursorStrategy
    cursor_field: str
    source_table: str
    limit: int


PRIORITY_ORDER: list[TableConfig] = [
    TableConfig("system_events", CursorStrategy.append, "edge_id", "system_events", 200),
    TableConfig("weather_minute_summary", CursorStrategy.summary, "change_seq", "weather_minute_summary", 500),
    TableConfig("lightning_minute_summary", CursorStrategy.summary, "change_seq", "lightning_minute_summary", 500),
    TableConfig("weather_quality_events", CursorStrategy.append, "edge_id", "weather_quality_events", 300),
    TableConfig("lightning_events", CursorStrategy.append, "edge_id", "lightning_events", 300),
    TableConfig("weather_samples", CursorStrategy.append, "edge_id", "weather_samples", 1000),
]

BY_NAME: dict[str, TableConfig] = {t.name: t for t in PRIORITY_ORDER}

_KNOWN = {t.value for t in TableName}
assert {t.name for t in PRIORITY_ORDER} == _KNOWN
