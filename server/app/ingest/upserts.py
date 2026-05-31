from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Text, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.lightning import LightningEvent, LightningMinuteSummary
from app.models.ops import SystemEvent, WeatherQualityEvent
from app.models.weather import WeatherMinuteSummary, WeatherSample
from petir_contracts import CursorStrategy, TableName

_APPEND_CONFLICT = ["node_id", "db_epoch", "edge_id"]
_SUMMARY_CONFLICT = ["node_id", "minute_utc", "source", "device"]

TABLE_SPEC: dict[str, dict[str, Any]] = {
    TableName.weather_samples.value: {
        "model": WeatherSample,
        "strategy": CursorStrategy.append,
        "conflict": _APPEND_CONFLICT,
        "cursor_field": "edge_id",
    },
    TableName.lightning_events.value: {
        "model": LightningEvent,
        "strategy": CursorStrategy.append,
        "conflict": _APPEND_CONFLICT,
        "cursor_field": "edge_id",
    },
    TableName.weather_quality_events.value: {
        "model": WeatherQualityEvent,
        "strategy": CursorStrategy.append,
        "conflict": _APPEND_CONFLICT,
        "cursor_field": "edge_id",
    },
    TableName.system_events.value: {
        "model": SystemEvent,
        "strategy": CursorStrategy.append,
        "conflict": _APPEND_CONFLICT,
        "cursor_field": "edge_id",
    },
    TableName.weather_minute_summary.value: {
        "model": WeatherMinuteSummary,
        "strategy": CursorStrategy.summary,
        "conflict": _SUMMARY_CONFLICT,
        "cursor_field": "change_seq",
    },
    TableName.lightning_minute_summary.value: {
        "model": LightningMinuteSummary,
        "strategy": CursorStrategy.summary,
        "conflict": _SUMMARY_CONFLICT,
        "cursor_field": "change_seq",
    },
}


def _model_columns(model: Any) -> dict[str, Any]:
    return {c.name: c for c in model.__table__.columns}


def _coerce(value: Any, column: Any) -> Any:
    if value is None:
        return None
    col_type = column.type
    if isinstance(col_type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value)
    if isinstance(col_type, Text) and isinstance(value, (list, dict)):
        return json.dumps(value)
    return value


def _to_db_row(
    row: dict[str, Any],
    cols: dict[str, Any],
    node_id: str,
    db_epoch: uuid.UUID,
    run_id: uuid.UUID,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if key == "ingest_run_id":
            out["edge_ingest_run_id"] = _coerce(value, cols["edge_ingest_run_id"])
        elif key in cols:
            out[key] = _coerce(value, cols[key])
    out["node_id"] = node_id
    out["db_epoch"] = db_epoch
    out["ingest_run_id"] = run_id
    return out


def upsert_rows(
    session: Session,
    node_id: str,
    db_epoch: uuid.UUID,
    run_id: uuid.UUID,
    table: str,
    valid_rows: list[dict[str, Any]],
) -> int:
    if not valid_rows:
        return 0
    spec = TABLE_SPEC[table]
    model = spec["model"]
    cols = _model_columns(model)
    payload = [_to_db_row(r, cols, node_id, db_epoch, run_id) for r in valid_rows]

    stmt = insert(model).values(payload)
    update_cols = {
        c: getattr(stmt.excluded, c)
        for c in payload[0].keys()
        if c not in spec["conflict"] and c != "id"
    }
    update_cols["synced_at_utc"] = text("now()")
    stmt = stmt.on_conflict_do_update(index_elements=spec["conflict"], set_=update_cols)
    session.execute(stmt)
    return len(payload)


def batch_max_cursor(table: str, rows: list[dict[str, Any]]) -> int | None:
    field = TABLE_SPEC[table]["cursor_field"]
    seen = [r[field] for r in rows if isinstance(r.get(field), int)]
    return max(seen) if seen else None


def cursor_strategy(table: str) -> CursorStrategy:
    return TABLE_SPEC[table]["strategy"]
