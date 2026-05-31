from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session

from app.models.ai import RetentionPolicy

_TABLE_TS_COLUMN = {
    "weather_samples": "created_at_utc",
    "weather_minute_summary": "minute_utc",
    "lightning_events": "created_at_utc",
    "lightning_minute_summary": "minute_utc",
    "weather_quality_events": "created_at_utc",
    "system_events": "ts_pi_utc",
}


def run_retention(session: Session) -> dict[str, Any]:
    policies = session.execute(
        select(RetentionPolicy).where(RetentionPolicy.enabled.is_(True))
    ).scalars().all()

    results: dict[str, int] = {}
    now = datetime.now(timezone.utc)

    for policy in policies:
        ts_col = _TABLE_TS_COLUMN.get(policy.table_name)
        if not ts_col:
            continue
        cutoff = now - timedelta(days=policy.retain_days)
        sql = text(
            f"DELETE FROM {policy.table_name} "
            f"WHERE {ts_col} < :cutoff"
        )
        result = session.execute(sql, {"cutoff": cutoff})
        pruned = result.rowcount
        results[policy.table_name] = pruned

        session.execute(
            update(RetentionPolicy)
            .where(RetentionPolicy.id == policy.id)
            .values(last_pruned_utc=now, rows_pruned_last=pruned)
        )

    session.commit()
    return {"pruned": results, "ran_at_utc": now.isoformat()}
