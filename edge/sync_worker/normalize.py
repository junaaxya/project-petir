from __future__ import annotations

from collections import defaultdict
from typing import Any

from petir_contracts import LightningStatus, SystemLevel, WeatherStatus

_WEATHER_STATUS_SYNONYMS = {"healthy": WeatherStatus.ok.value}
_SYSTEM_LEVEL_SYNONYMS = {"warning": SystemLevel.warn.value}
_LIGHTNING_STATUS_SYNONYMS = {
    "noisy": LightningStatus.noise.value,
    "active": LightningStatus.activity.value,
}

_FIELD_SYNONYMS: dict[str, tuple[str, dict[str, str]]] = {
    "weather_minute_summary": ("status", _WEATHER_STATUS_SYNONYMS),
    "system_events": ("level", _SYSTEM_LEVEL_SYNONYMS),
    "lightning_minute_summary": ("status", _LIGHTNING_STATUS_SYNONYMS),
}

normalized_counts: dict[str, int] = defaultdict(int)


def normalize_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    spec = _FIELD_SYNONYMS.get(table)
    if spec is None:
        return row
    field, mapping = spec
    value = row.get(field)
    if isinstance(value, str) and value in mapping:
        row[field] = mapping[value]
        normalized_counts[f"{table}.{field}:{value}->{mapping[value]}"] += 1
    return row
